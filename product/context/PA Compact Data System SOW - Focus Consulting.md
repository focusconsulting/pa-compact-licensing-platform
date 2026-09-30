![][image1]

---

# STATEMENT OF WORK

**Occupational Licensure Compact Data System: MVP Development**

| Prepared by | Focus Consulting LLC (Focus) 1701 Rhode Island Ave NW, 2nd Floor Washington, DC 20036 POC: Phedra Arthur ([phedra.arthur@focusconsulting.io](mailto:phedra.arthur@focusconsulting.io)) |
| :---- | :---- |
| Prepared for | Physician Assistant Compact Commission (The Commission) |
| Version | 1.0 \- 03/09/2026 |
| Anticipated Kick-off | 04/01/2026 |
| Contract Type | Time and Materials |
| Not‑To‑Exceed Amount | \$270,000 |
| Period of Performance | 16 weeks |

# **1\. Background and Purpose**

The Physician Assistant Compact Commission administers the Physician Assistant Licensure Compact and is responsible for enabling licensed physician assistants to obtain practice privileges across participating states.To operationalize the compact, the Commission requires a secure digital data system that enables issuance and management of interstate practice privileges while ensuring appropriate data security and transparency.

This Statement of Work (SOW) establishes the scope, deliverables, schedule, staffing, and operating terms for Focus Consulting LLC's (Focus) development of the PA Compact Commission's Occupational Licensure Data System. This document reflects Focus' original proposal submitted December 19, 2025, and incorporates clarifications provided in response to the Commission's follow-up questions of February 3, 2026\.

Focus will design and build a pilot ready Minimum Viable Product (MVP) data system supporting these objectives within the period of performance defined in this Statement of Work.

# **2\. Scope of Work**

Focus will design, develop, and deliver a **Minimum Viable Product (MVP)** data system enabling the PA Compact Commission to operationalize issuance of compact practice privileges.

The MVP scope will prioritize workflows necessary for the Commission to issue compact privileges and will align with priority user stories identified in the RFP.

Specific features and implementation details will be prioritized collaboratively through backlog refinement during project delivery.

The MVP will be pilot‑ready and production‑grade, secure and accessible, and designed to support both manual and future automated workflows.

## **2.1 Core MVP Functional Capabilities**

### **Physician Assistant Portal**

The system will enable physician assistants to:

* Portal authentication  
* Submit qualifying license for verification  
* Submit required information and documentation  
* Apply for compact privileges online  
* Pay application fees associated with the privilege application  
* Track application status  
* Receive notifications regarding privilege processing  
* Receive confirmation of privilege issuance  
* Receive renewal notifications  
* View state practice requirements

### **State Licensing Administrator Portal**

The system will enable participating state administrators to:

* Portal authentication  
* Verify qualifying licenses  
* Issue compact privileges  
* Access practitioner records related to compact participation  
* Update license or privilege status  
* Upload disciplinary information

### **Commission Administrative Portal**

The system will enable Commission staff to:

* Portal authentication  
* Access system dashboards to monitor privilege applications and issuance  
* Generate basic operational reports

### **Public Privilege Verification**

The system will include a public interface allowing users to verify active physician assistant compact privileges.

## **2.2 Out of Scope**

Unless prioritized and achievable within the Period of Performance and contract ceiling, the following capabilities are not guaranteed within the MVP scope:

* Real‑time or API integrations with state licensing systems  
* Integrations with national credentialing organizations  
* Advanced reporting or analytics platforms  
* Digital credential wallets or verifiable credentials  
* Enterprise identity federation or SSO integrations  
* Advanced identity proofing systems  
* Payment reconciliation and financial reporting  
* Support tooling

Such capabilities may be addressed in future phases subject to additional funding and engagement.

## **2.3 MVP Success Criteria**

Per Commission guidance, MVP success is defined as a system that enables the Commission to issue compact privileges, with additional features prioritized collaboratively through the agile process. The 72-hour privilege issuance goal is an operational target to be refined through the agile process, not a system-level SLA.

Acceptance will occur upon:

* Deployment of the MVP system to a production-grade pilot environment  
* Demonstration of core privilege issuance workflows  
* Compliance with accessibility and testing standards  
* Delivery of documentation and repositories

# **3\. Phased Delivery Approach**

Focus will deliver the MVP across three phases over 16 weeks (8 sprints). Scope within each phase will be collaboratively refined with the Commission's Product Owner through an agile, sprint-based process.

## **Phase 1 – Discovery and Foundations (Weeks 1–4)**

* Stakeholder workshops and interviews  
* User research and core user journey validation  
* Backlog refinement and prioritization  
* UX Design  
* Canonical data model definition  
* Software development environment setup  
* Continuous testing and deployment pipeline setup  
* Cloud environment provisioning  
* Security baseline configuration

## **Phase 2 – Core Development (Weeks 5–12)**

* License verification workflows  
* Privilege application workflows  
* Application fee payment integration  
* Privilege issuance workflows  
* Commission administrative functionality  
* Public verification capability  
* Usability testing

## **Phase 3 – Hardening and Pilot Readiness (Weeks 13–16)**

* Usability refinements  
* Complete automated test coverage  
* UAT testing and bug fixing  
* Security validation (OWSAP)  
* Accessibility compliance testing (WCAG 2.1 AA)  
* Finalize documentation and system diagrams  
* Deployment readiness validation  
* Deploy to production-grade, pilot ready environment

# **4\. Agile Delivery and Sprint Review Process**

## **4.1 Sprint Cadence**

Focus will operate in two-week sprints throughout the period of performance. The following ceremonies will be conducted each sprint:

* Sprint Planning: Focus and the Commission's Product Owner jointly review and prioritize the backlog  
* Daily Stand-ups: Brief synchronous check-ins; the Commission's Product Owner will participate  
* Sprint Reviews / Demos: Live demonstrations of completed data system components at the end of every sprint. Commissioners and stakeholders are welcome to attend  
* Sprint Retrospectives: The delivery team process improvement sessions

## **4.2 How the Commission Can Track Progress**

The Commission will have full visibility into progress through multiple mechanisms:

* Sprint demos held at the close of every two-week sprint, open to Commissioners and stakeholders. Components will be demonstrated in a live staging environment, not slides  
* Continuous access to the Commission-owned GitHub repository, where all code, commits, and CI/CD pipeline results are visible in real time  
* Shared project management tooling (e.g., Jira or equivalent) providing a live view of the backlog, sprint progress, and acceptance criteria  
* Usability research artifacts (plans, session notes, synthesis) delivered at the end of each applicable sprint

## **4.3 Usability Testing Cadence**

Usability testing is embedded throughout all phases of delivery, and not limited to Phase 3\. Focus will conduct iterative user research with physician assistants and state licensing staff at regular intervals, with research artifacts made available at the end of each applicable sprint. The Commission will assist with recruiting end users for testing sessions.

## **4.4 Backlog Prioritization**

The Commission does not have a pre-prioritized product backlog. Prioritization will occur collaboratively during sprint planning with the Commission's Product Owner. Focus will maintain a living backlog and surface trade-off decisions transparently when scope, budget, or timeline tensions arise.

# **5\. Deliverables and Quality Standards**

## **5.1 Deliverables**

Deliverables for this SOW will include:

* User research artifacts  
* UI design artifacts  
* Usability testing artifacts  
* Product backlog and sprint activity documentation  
* Production‑grade, pilot ready MVP application  
* Open‑source source code repository  
* CI/CD pipeline  
* Infrastructure‑as‑Code scripts  
* System architecture documentation  
* Security scan reports  
* Transition documentation

## **5.2 Quality Standards**

All deliverables must meet the quality standards set forth in the PA Compact Commission's Quality Assurance Surveillance Plan (QASP). The following table summarizes each deliverable, the applicable standard, and the acceptable quality level.

| Deliverable | Performance Standard | Acceptable Quality Level | Assessment Method |
| :---- | :---- | :---- | :---- |
| **Tested Code** | Version-controlled code in Commission-designated GitHub repository | Minimum 90% test coverage; all areas meaningfully tested | Manual review \+ automated testing |
| **Properly Styled Code** | GSA 18F Front-End Guide | 0 linting errors and 0 warnings. | Manual review \+ automated testing |
| **Accessible UI** | WCAG 2.1 AA standards (Section 508 if also applicable) | 0 automated errors (Pa11y or equivalent); 0 manual testing errors | Automated scanner \+ manual testing per sprint |
| **Deployed System** | Code successfully builds and deploys into dev, test, and production environments | Successful build with a single command. | Manual review \+ automated testing |
| **Documentation** | All dependencies listed with licenses; major functionality documented; inline method documentation (JSDoc-compatible); system architecture diagram provided | Complete and current at each sprint | Manual review |
| **Secure Code** | OWASP ASVS 3.0; code free of medium- and high-level static and dynamic vulnerabilities | Clean results from static testing (e.g., Snyk, npm audit, or stack-appropriate equivalent) and OWASP ZAP; documented false positives | Automated security scanning and static testing results |
| **User Research Artifacts** | Usability testing and user research conducted at regular intervals throughout development | Research plans and artifacts available at end of every applicable sprint, per contractor's research plan | Manual evaluation by Commission per research plan |
| **Sprint Demo Artifacts** | Live demonstration of working software at close of each sprint | Functional demo in staging environment | Commission attendance and review. Video recordings available. |

## **5.3 Transition and Follow On**

Pilot launch, system operations, and maintenance are anticipated to occur under a separate statement of work and period of performance. If no follow-on contract is funded, or Focus is not selected for a follow-on engagement, Focus will provide system documentation and knowledge transfer sufficient to enable the Commission or a future contractor to assume operational responsibility.

Transition deliverables will include:

* Transfer for code repository to the Commision  
* Transfer of cloud services account to the Commision  
* Transfer of any logging and monitoring services to the Commission  
* Transfer of any third party account credentials to the Commission

# **6\. Staffing and Pricing**

## **6.1 Team Composition**

Focus will staff the project with a small, senior-leaning, cross-functional team. Level of effort varies by phase to align skills with delivery needs. The table below identifies expected levels of effort by each team member across the three phases. The level of effort may be adjusted across phases through the agile process as requirements and product backlog are finalized.

| Role | Phase 1 FTE | Phase 2 FTE | Phase 3 FTE |
| :---- | :---- | :---- | :---- |
| **Project Manager / Product Lead (Key Personnel)** | 80% | 50% | 30% |
| **Technical Lead (Key Personnel)** | 80% | 100% | 50% |
| **Fullstack Software Engineer** | 100% | 100% | 50% |
| **UX Designer / Researcher** | 100% | 50% | 15% |

### **6.1.1 Key Personnel**

Two Key Personnel are designated in accordance with the RFP and will stay engaged throughout the full period of performance to ensure continuity

**Kevon Paynter (Project Manager / Product Lead)**: Experienced and passionate product and project manager in civic tech and impact space with expertise in end-to-end software delivery and high stakes launches. Currently lead product manager at Focus on the Minnesota Paid Leave project.

**Jamie Albinson (Tech Lead)**: A senior software engineer with 15 years of experience designing and building scalable, secure systems in regulated domains. Proven track record delivering high-throughput microservices using Javascript, Kotlin, Scala, and Java, with expertise in distributed systems, API design, and cloud-native infrastructure. Strong technical leader who mentors engineers, drives architectural decisions, and partners across teams to deliver reliable, high-impact software.

## **6.2 Pricing**

The pricing table below reflects the total expected hours by functional area. Please note that we are providing a blended rate for software engineer roles to account for some flexibility in shifting FTE allocations across phases as needed.

| Role | Hourly Rate | Estimated Total Hours | Estimated Cost |
| ----- | ----- | ----- | ----- |
| **Product Manager** | \$175.61 | 311 | \$54,614.71 |
| **Software Engineer** | \$167.82 | 1006 | \$168,826.92 |
| **UX Designer** | \$146.13 | 318 | \$46,469.34 |
| **Total** |  |  | **\$269,910.97** |

# **7\. Technical Approach**

## **7.1 Architecture**

Focus will build the data system on a modular, API-first architecture centered on a canonical compact data model representing practitioners, qualifying licenses, and derived interstate privileges. Core services will be exposed through documented REST APIs, enabling current MVP workflows and future state system integrations without system re-architecture.

## **7.2 Hosting and Cloud Infrastructure**

The system will be deployed in commercial cloud infrastructure, Amazon Web Services (AWS) or equivalent.

Focus will provision and manage hosting during the period of performance using Infrastructure‑as‑Code practices.

The Commission will assume responsibility for long‑term hosting costs following this period of performance.

Focus is not responsible for long‑term operational hosting or service‑level guarantees beyond the MVP delivery period unless agreed to in writing in a follow on statement of work. 

## **7.3 Security and Compliance**

The system will implement security best practices including:

* Encryption of data in transit and at rest  
* Role‑based access control  
* Comprehensive audit logging  
* OWASP‑aligned secure development practices  
* WCAG 2.1 AA accessibility compliance  
* Automated testing coverage  
* Zero trust principles

## **7.4 Payment Processor Integration**

Focus will integrate a payment processor selected by the Commission to support application fee payments. Focus may present payment processor options to the commission. Focus will implement secure integration practices but will not serve as the merchant of record and will not be responsible for financial reconciliation or settlement.

## **7.5 Intellectual Property and Open Source**

All developed software and documentation will be owned by the Commission and released as open source.

Focus retains ownership of pre‑existing proprietary tools and reusable components. Focus may use frameworks, templates, libraries, accelerators, and configuration scripts developed independently of this project to support delivery. Such materials remain the property of Focus and are not considered project deliverables. Focus retains the right to reuse knowledge, methodologies, architectural patterns, and non‑project‑specific code developed during the engagement.

# **8\. Contract Terms and Administration**

## **8.1 Payment Terms**

Invoices will be submitted monthly based on actual hours worked. Payment will be due within **15 days** of invoice submission.

## **8.2 Place of Performance**

Focus will perform work remotely. All team members are available during core Commission working hours of 10:00 a.m. – 4:00 p.m. ET.

## **8.3 Assumptions and Dependencies**

An assumptions log will be maintained throughout delivery.

Project timelines and functionality may depend on and impact by external factors including:

* Availability of product owner  
* Availability of user research and usability testing participants  
* Payment processor selection and integration  
* Regulatory or policy decisions

### **8.3.1 Stakeholder Availability and Decision Timeliness**

The project delivery schedule and sprint commitments assume timely availability of Commission stakeholders for required project activities, including product backlog prioritization, sprint planning, usability testing participation, and acceptance of completed work.

If required stakeholders are unavailable, fail to participate in scheduled ceremonies, or do not provide required decisions within the timeframes described in Section 8.3.2 below, Focus will notify the Commission and document the impact in the project assumptions log.

Where such delays materially affect delivery timelines, Focus and the Commission will collaboratively determine an appropriate:

* adjustment of the delivery schedule,  
* reprioritization of the product backlog, or  
* initiation of a formal change request.

A change request may be initiated where delays or revised direction result in:

* material rework of completed deliverables,  
* additional development work beyond the originally planned backlog scope, or  
* extension of the Period of Performance.

Any approved change request that increases the level of effort beyond the Not-To-Exceed amount or extends the Period of Performance will require written authorization from the Commission before additional work proceeds.

### **8.3.2 Stakeholder Engagement Expectations**

To support efficient agile delivery, the Commission will designate a Product Owner and ensure reasonable availability of key stakeholders throughout the Period of Performance.

The following engagement expectations apply:

| Engagement Activity | Expected Commission Participation |
| :---- | :---- |
| Sprint Planning | Product Owner attendance each sprint |
| Sprint Reviews / Demos | Product Owner attendance; Commissioners and stakeholders encouraged |
| Daily Standups | Product Owner participation when feasible |
| Product Backlog Prioritization | Product Owner provides prioritization decisions within 2 business days |
| Usability Testing | Commission assists in identifying or recruiting representative end users in time for anticipated start for testing |
| Policy / Regulatory Clarifications | Commission provides guidance within 3 business days where required for system implementation |
| Acceptance of Completed Work | Product Owner reviews sprint deliverables within 3 business days |

If feedback or decisions are not received within the timeframes above, Focus may proceed using reasonable assumptions in order to maintain project momentum. Any resulting changes requested later may require backlog reprioritization or adjustment to project scope.

## **8.4 Limitation of Liability**

To the fullest extent permitted by law, Focus Consulting LLC's total cumulative liability under this Statement of Work shall not exceed the total fees paid under this agreement.

Focus shall not be liable for indirect, incidental, consequential, or punitive damages including loss of revenue, loss of data, or service interruption.

## **8.5 Policy and Regulatory Responsibility**

Focus is responsible solely for software development under this Statement of Work. Interpretation of compact legislation, regulatory compliance decisions, practitioner eligibility determinations, and operational use of the system remain the responsibility of the Commission and participating states.

# **9\. SIGNATURES**

This Statement of Work becomes effective upon execution by authorized representatives of both parties.

**Physician Assistant Compact Commission**

Name: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Title: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Signature: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

**Focus Consulting LLC**

Name: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Title: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Signature: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAAAcCAYAAACeeLqCAAACMUlEQVR4Xu2YwU0sMRQEHQIhEAqhEAKhkAFkQEgbCmgQXnnL3X49A8tpSurDn1fdQkb6B1pb87nIyR3hY7uc3AE+8ionf8xbmx/Z5eQO8JHVg7/i3yd/CB+dj39yZ/jw5y/gn+HDn7+Af4SPvsoKuipH4Y6Lgo7zRugf7ahc4SGJg16VFPaSEN6VQ+ivOvTSTB+SKOikqaCfREHHeSP0XefSZi/JN/yYhPC+Nw56aRR0nDdC33XopJmgYMUBuqse787r0Et9BTecN0Lfdeg4r2PvHEnHVBz0nH9ps6O8FO4kW/Rdh47zSjiSjNGt/A36qsO781K4k2zRdx06lW9huRqhV/kd+qrDu/NSuJNs0XcdOioRLFVlepXfob/lcmPM9y3b36GOwq2jP6eDnssSylWJXuV36Kseb7zvhVvJHv2qQ3cVCaWl3Gav8jv0VY833vfCrWSPftJ5b3PHZYKCFX+gV/kd+lseR2H4zhyFO8kW/aQzwq7KDTxKaYBe5Xfoqw7vzkvhTrX10Ga/6ji4Yfd4lBKge8RXHd6dl8Kdao9e5VdwR+7xKCVAt+rQc/5Lmx3njrg7N6otepWfwK1pj0cpgac2+z3PV2u+Jfv0Vp3VbYN95/PGKKr7Bnekz6OUBPT3xkEvjcL9n743CjppHhug0JPATpoK+kkc9Kp8iG8KOmkmKFjRwF6VFPaqrKDr0nHfR+gkkVBaygvYH/ObPydc2rx39Odk121U9xG6Kjd8AUgQFbZ7TLb0AAAAAElFTkSuQmCC>