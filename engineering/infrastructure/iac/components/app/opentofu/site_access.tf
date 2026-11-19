# The site password (SCRUM-139). Where site_password_protected is on, CloudFront answers
# nothing without it, pages or API, so an environment that is not yet public cannot be
# read from the internet.
#
# Pages ask for it with HTTP basic auth. The API cannot: the client's Authorization
# header carries the Cognito token. So a page's response sets a cookie, and the API's
# cache behaviour asks for that instead.
#
# The functions hold only a hash. The password is generated here and read from the
# secret; to change it, bump site_access's secret_string_wo_version and run
#   tofu apply -replace='random_password.site_access[0]'

locals {
  site_access_username = "pacompact"
}

resource "random_password" "site_access" {
  count = var.site_password_protected ? 1 : 0

  length = 32
  # Typed or pasted into a browser's prompt.
  special = false
}

resource "aws_secretsmanager_secret" "site_access" {
  count = var.site_password_protected ? 1 : 0

  name       = "${var.environment_name}-site-access"
  kms_key_id = aws_kms_key.data.arn
}

resource "aws_secretsmanager_secret_version" "site_access" {
  count = var.site_password_protected ? 1 : 0

  secret_id                = aws_secretsmanager_secret.site_access[0].id
  secret_string_wo_version = 1
  secret_string_wo = jsonencode({
    username = local.site_access_username
    password = random_password.site_access[0].result
  })
}

locals {
  # The Authorization header a browser sends once the password is entered.
  site_access_header = one([
    for password in random_password.site_access :
    "Basic ${base64encode("${local.site_access_username}:${password.result}")}"
  ])

  # The cookie is the header's hash, and the functions hold the hash of that: reading a
  # function's code gives neither the password nor a cookie that works.
  site_access_cookie = "site-access"
  site_access_js     = !var.site_password_protected ? "" : <<-EOF
    var crypto = require("crypto");
    function sha256(value) {
      return crypto.createHash("sha256").update(value).digest("hex");
    }
    function allowed(value) {
      return sha256(value) === "${nonsensitive(sha256(sha256(local.site_access_header)))}";
    }
    function byPassword(request) {
      var header = request.headers.authorization;
      return header !== undefined && allowed(sha256(header.value));
    }
    function byCookie(request) {
      var cookie = request.cookies["${local.site_access_cookie}"];
      return cookie !== undefined && allowed(cookie.value);
    }
  EOF

  # In page_html (cdn.tf), which is the pages' viewer-request function either way.
  site_access_page_guard = !var.site_password_protected ? "" : <<-EOF
    if (!byPassword(event.request)) {
      return {
        statusCode: 401,
        statusDescription: "Unauthorized",
        headers: { "www-authenticate": { value: 'Basic realm="PA Compact ${var.environment_name}"' } },
      };
    }
  EOF
}

# Runs on a page's response, so only after page_html let the request through. CloudFront
# skips it when the origin answers 400 or more; the page's scripts and styles set the
# cookie then.
resource "aws_cloudfront_function" "site_access_cookie" {
  count = var.site_password_protected ? 1 : 0

  name    = "${var.environment_name}-${local.application_name}-site-access-cookie"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOF
    ${local.site_access_js}
    function handler(event) {
      var response = event.response;
      if (byPassword(event.request)) {
        response.cookies["${local.site_access_cookie}"] = {
          value: sha256(event.request.headers.authorization.value),
          attributes: "Path=/api; Secure; HttpOnly; SameSite=Strict",
        };
      }
      return response;
    }
  EOF
}

resource "aws_cloudfront_function" "site_access_api" {
  count = var.site_password_protected ? 1 : 0

  name    = "${var.environment_name}-${local.application_name}-site-access-api"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOF
    ${local.site_access_js}
    function handler(event) {
      var request = event.request;
      // No WWW-Authenticate: a browser would prompt in the middle of a page.
      if (!byCookie(request)) {
        return { statusCode: 401, statusDescription: "Unauthorized" };
      }
      // The API has no use for it.
      delete request.cookies["${local.site_access_cookie}"];
      return request;
    }
  EOF
}
