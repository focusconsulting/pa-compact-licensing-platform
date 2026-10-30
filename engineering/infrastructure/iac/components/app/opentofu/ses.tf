# Email from the Worker through SES's SMTP interface (backlog D7, ADR-0014), sent from
# no-reply@<environment's hosted zone> with DKIM, SPF on a custom MAIL FROM domain, and DMARC.
#
# A new account's SES is in the sandbox: it sends only to verified addresses until
# production access is requested for the account, outside OpenTofu.

locals {
  email_domain     = local.hosted_zone_name
  mail_from_domain = "mail.${local.email_domain}"
}

resource "aws_sesv2_email_identity" "domain" {
  email_identity = local.email_domain

  dkim_signing_attributes {
    next_signing_key_length = "RSA_2048_BIT"
  }
}

resource "aws_route53_record" "ses_dkim" {
  count   = 3 # Easy DKIM always issues three tokens.
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "${aws_sesv2_email_identity.domain.dkim_signing_attributes[0].tokens[count.index]}._domainkey.${local.email_domain}"
  type    = "CNAME"
  ttl     = 600
  records = ["${aws_sesv2_email_identity.domain.dkim_signing_attributes[0].tokens[count.index]}.dkim.amazonses.com"]
}

# Bounces go to mail.<domain>, so SPF aligns with the From domain for DMARC.
resource "aws_sesv2_email_identity_mail_from_attributes" "domain" {
  email_identity         = aws_sesv2_email_identity.domain.email_identity
  mail_from_domain       = local.mail_from_domain
  behavior_on_mx_failure = "REJECT_MESSAGE"
}

resource "aws_route53_record" "ses_mail_from_mx" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = local.mail_from_domain
  type    = "MX"
  ttl     = 600
  records = ["10 feedback-smtp.${var.aws_region}.amazonses.com"]
}

resource "aws_route53_record" "ses_mail_from_spf" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = local.mail_from_domain
  type    = "TXT"
  ttl     = 600
  records = ["v=spf1 include:amazonses.com -all"]
}

# Quarantine anything claiming the domain that fails both DKIM and SPF alignment.
resource "aws_route53_record" "dmarc" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "_dmarc.${local.email_domain}"
  type    = "TXT"
  ttl     = 600
  records = ["v=DMARC1; p=quarantine; adkim=s; aspf=s"]
}

# SMTP needs an access key, which a task role cannot provide. The user may send only from
# the domain's no-reply address. Rotate with `tofu apply -replace=aws_iam_access_key.ses_smtp`,
# then force a new Worker deployment.
resource "aws_iam_user" "ses_smtp" {
  name = "${var.environment_name}-${local.application_name}-ses-smtp"
}

resource "aws_iam_user_policy" "ses_smtp_send" {
  name = "${var.environment_name}-${local.application_name}-ses-send"
  user = aws_iam_user.ses_smtp.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "ses:SendRawEmail"
      Resource  = aws_sesv2_email_identity.domain.arn
      Condition = { StringEquals = { "ses:FromAddress" = "no-reply@${local.email_domain}" } }
    }]
  })
}

resource "aws_iam_access_key" "ses_smtp" {
  user = aws_iam_user.ses_smtp.name
}

resource "aws_secretsmanager_secret" "ses_smtp" {
  name = "${var.environment_name}-ses-smtp"
}

# The SMTP password is derived from the access key's secret for this region.
resource "aws_secretsmanager_secret_version" "ses_smtp" {
  secret_id = aws_secretsmanager_secret.ses_smtp.id
  secret_string = jsonencode({
    username = aws_iam_access_key.ses_smtp.id
    password = aws_iam_access_key.ses_smtp.ses_smtp_password_v4
  })
}
