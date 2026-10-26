"""
ContractLens Evaluation Suite — Synthetic Contract Dataset
===========================================================

Five synthetic contracts with known clause structures for reproducible
retrieval and generation benchmarks.  Each contract is crafted so that
the ground-truth answers to the test questions are *deterministic* —
they can be verified by substring match without any LLM call.

Contracts
---------
1. ACME–BetaCorp Master Services Agreement  (full, balanced)
2. Omega–Sigma Software Licence              (one-sided, missing clauses)
3. Delta–Epsilon Employment Bond             (Indian jurisdiction, enforceability)
4. GreenLeaf–TerraCo Supply Agreement        (conflicting clauses)
5. NovaHealth–MediCore Data Processing       (data-heavy, GDPR/CCPA)
"""

from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class SyntheticContract:
    """A synthetic contract document with known clause structure."""
    contract_id: str
    filename: str
    title: str
    jurisdiction: str
    description: str
    full_text: str
    # Map of clause category -> list of section headings present
    present_clauses: Dict[str, List[str]] = field(default_factory=dict)
    # Categories intentionally omitted
    absent_clauses: List[str] = field(default_factory=list)
    # Categories with internal contradictions
    conflicting_clauses: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Contract 1 — Balanced Master Services Agreement
# ---------------------------------------------------------------------------
CONTRACT_ACME_BETA = SyntheticContract(
    contract_id="eval_acme_beta_001",
    filename="ACME_BetaCorp_MSA.pdf",
    title="ACME–BetaCorp Master Services Agreement",
    jurisdiction="Delaware, USA",
    description="A balanced MSA with all 8 standard clause categories present.",
    present_clauses={
        "Termination": ["Section 8 — Termination"],
        "Indemnification": ["Section 10 — Indemnification"],
        "Liability Limits": ["Section 11 — Limitation of Liability"],
        "Confidentiality": ["Section 12 — Confidentiality"],
        "Payment": ["Section 5 — Payment Terms"],
        "Automatic Renewal": ["Section 3.2 — Renewal"],
        "Data Protection": ["Section 14 — Data Protection"],
        "Dispute Resolution": ["Section 16 — Governing Law"],
    },
    absent_clauses=[],
    conflicting_clauses=[],
    full_text="""MASTER SERVICES AGREEMENT

This Master Services Agreement ("Agreement") is entered into as of January 15, 2025,
by and between ACME Corporation, a Delaware corporation ("Client"),
and BetaCorp Solutions LLC, a California limited liability company ("Provider").

Section 1 — Scope of Services
Provider shall deliver the software development, integration, and support services
described in each Statement of Work ("SOW") executed under this Agreement.

Section 2 — Term
This Agreement commences on the Effective Date and continues for an initial term
of twenty-four (24) months unless earlier terminated in accordance with Section 8.

Section 3 — Renewal
3.1 Initial Term. The initial term is twenty-four (24) months from the Effective Date.
3.2 Renewal. This Agreement shall automatically renew for successive twelve (12)
month periods unless either party provides written notice of non-renewal at least
sixty (60) days prior to the expiration of the then-current term.

Section 4 — Fees
Client agrees to pay the fees specified in each SOW. All fees are quoted in United
States Dollars (USD) and are exclusive of applicable taxes.

Section 5 — Payment Terms
5.1 Invoicing. Provider shall issue invoices monthly in arrears for services performed.
5.2 Due Date. All undisputed invoices are due and payable within thirty (30) days
of the invoice date ("Net 30").
5.3 Late Payment. Overdue undisputed amounts shall accrue interest at the lesser of
one and one-half percent (1.5%) per month or the maximum rate permitted by law.
5.4 Disputed Invoices. Client shall notify Provider of any disputed invoice line items
within fifteen (15) days of receipt; undisputed portions remain payable per Section 5.2.

Section 6 — Intellectual Property
6.1 Pre-existing IP. Each party retains all rights to its pre-existing intellectual property.
6.2 Work Product. All deliverables created under a SOW vest exclusively in Client
upon full payment of the corresponding fees.

Section 7 — Representations and Warranties
Provider represents that services will be performed in a professional manner consistent
with generally accepted industry standards.

Section 8 — Termination
8.1 Termination for Convenience. Either party may terminate this Agreement for
convenience upon ninety (90) days prior written notice to the other party.
8.2 Termination for Cause. Either party may terminate this Agreement immediately
upon written notice if the other party commits a material breach and fails to cure
such breach within thirty (30) days of receiving written notice thereof.
8.3 Effect of Termination. Upon termination, Client shall pay all undisputed fees for
services performed through the effective date of termination.

Section 9 — Force Majeure
Neither party shall be liable for delays caused by events beyond its reasonable control.

Section 10 — Indemnification
10.1 Provider Indemnification. Provider shall indemnify, defend, and hold harmless
Client against all third-party claims arising from Provider's gross negligence,
willful misconduct, or infringement of third-party intellectual property rights.
10.2 Client Indemnification. Client shall indemnify Provider against all third-party
claims arising from Client's misuse of the deliverables beyond the scope authorized
under this Agreement.
10.3 Indemnification Cap. Each party's aggregate indemnification obligation shall
not exceed the total fees paid or payable under this Agreement during the twelve (12)
months preceding the event giving rise to the claim.

Section 11 — Limitation of Liability
11.1 Aggregate Cap. EXCEPT FOR OBLIGATIONS ARISING UNDER SECTIONS 10
(INDEMNIFICATION) AND 12 (CONFIDENTIALITY), EACH PARTY'S TOTAL AGGREGATE
LIABILITY UNDER THIS AGREEMENT SHALL NOT EXCEED THE TOTAL FEES PAID OR
PAYABLE DURING THE TWELVE (12) MONTHS PRECEDING THE CLAIM.
11.2 Consequential Damages Waiver. IN NO EVENT SHALL EITHER PARTY BE LIABLE
FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES,
INCLUDING LOSS OF PROFITS, REVENUE, DATA, OR BUSINESS OPPORTUNITY.

Section 12 — Confidentiality
12.1 Definition. "Confidential Information" means all non-public information disclosed
by either party designated as confidential or that reasonably should be understood
as confidential.
12.2 Obligations. The receiving party shall protect Confidential Information using
at least the same degree of care it uses to protect its own confidential information,
but no less than reasonable care.
12.3 Exceptions. Confidential Information excludes information that: (a) is publicly
available; (b) was lawfully known prior to disclosure; (c) is independently developed;
or (d) is required to be disclosed by law or court order.
12.4 Survival. Confidentiality obligations survive termination for three (3) years;
trade secrets survive indefinitely.

Section 13 — Insurance
Provider shall maintain professional liability insurance with limits of no less than
$2,000,000 per occurrence.

Section 14 — Data Protection
14.1 Compliance. Each party shall comply with applicable data protection laws,
including the General Data Protection Regulation (GDPR) and the California Consumer
Privacy Act (CCPA) to the extent applicable.
14.2 Data Processing Agreement. If Provider processes personal data on behalf of
Client, the parties shall execute a Data Processing Addendum ("DPA") conforming
to Article 28 GDPR.
14.3 Security Standards. Provider shall implement and maintain reasonable technical
and organizational security measures, including encryption at rest and in transit.
14.4 Breach Notification. Provider shall notify Client of any confirmed personal data
breach within forty-eight (48) hours of discovery.
14.5 Data Return. Upon termination, Provider shall return or securely destroy all
personal data within thirty (30) days.

Section 15 — Audit Rights
Client may, upon thirty (30) days' notice, audit Provider's compliance with this
Agreement, including data protection obligations, no more than once per calendar year.

Section 16 — Governing Law and Dispute Resolution
16.1 Governing Law. This Agreement is governed by the laws of the State of Delaware,
without regard to conflict-of-laws principles.
16.2 Dispute Resolution. The parties agree to attempt good-faith negotiation for thirty
(30) days. If unresolved, disputes shall be submitted to binding commercial arbitration
administered by the American Arbitration Association (AAA) in Wilmington, Delaware.

Section 17 — Entire Agreement
This Agreement, together with all executed SOWs, constitutes the entire agreement
between the parties and supersedes all prior negotiations and agreements.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first
written above.

ACME Corporation                    BetaCorp Solutions LLC
By: ___________________             By: ___________________
Name: Jane Mitchell, CEO            Name: Raj Patel, Managing Director
Date: January 15, 2025              Date: January 15, 2025
""",
)


# ---------------------------------------------------------------------------
# Contract 2 — One-sided Software Licence (missing key clauses)
# ---------------------------------------------------------------------------
CONTRACT_OMEGA_SIGMA = SyntheticContract(
    contract_id="eval_omega_sigma_002",
    filename="Omega_Sigma_Software_Licence.pdf",
    title="Omega–Sigma Software Licence Agreement",
    jurisdiction="New York, USA",
    description="A vendor-biased licence with missing liability limits, no data protection, and one-sided indemnity.",
    present_clauses={
        "Termination": ["Section 6 — Termination"],
        "Indemnification": ["Section 7 — Indemnification"],
        "Payment": ["Section 3 — Licence Fees"],
        "Confidentiality": ["Section 8 — Confidentiality"],
        "Dispute Resolution": ["Section 10 — Governing Law"],
    },
    absent_clauses=["Liability Limits", "Automatic Renewal", "Data Protection"],
    conflicting_clauses=[],
    full_text="""SOFTWARE LICENCE AGREEMENT

This Software Licence Agreement ("Agreement") is entered into as of March 1, 2025,
by and between Omega Systems Inc., a New York corporation ("Licensor"),
and Sigma Analytics Ltd., a UK limited company ("Licensee").

Section 1 — Grant of Licence
Licensor grants Licensee a non-exclusive, non-transferable licence to use the
OmegaAnalytics v4.5 platform ("Software") during the Licence Term.

Section 2 — Licence Term
The licence is granted for an initial period of twelve (12) months commencing on the
Effective Date. The Agreement expires at the end of the term without automatic renewal.

Section 3 — Licence Fees
3.1 Annual Fee. Licensee shall pay an annual licence fee of $120,000 USD.
3.2 Payment Due Date. The full annual fee is due within fifteen (15) days of the
Effective Date and each anniversary thereafter.
3.3 No Refunds. All fees paid are non-refundable under any circumstances.

Section 4 — Restrictions
Licensee shall not reverse-engineer, decompile, or create derivative works from the Software.

Section 5 — Support
Licensor shall provide standard business-hours email support. Premium 24/7 support
is available at additional cost.

Section 6 — Termination
6.1 Termination by Licensor. Licensor may terminate this Agreement immediately upon
written notice if Licensee breaches any provision hereof.
6.2 Termination by Licensee. Licensee may terminate only at the end of the then-current
Licence Term by providing sixty (60) days prior written notice.
6.3 No Cure Period. Licensor's right to terminate for breach is immediate and does not
require a cure period.

Section 7 — Indemnification
7.1 Licensee Indemnity. Licensee shall indemnify, defend, and hold harmless Licensor
and its officers, directors, and employees against any and all claims, losses, damages,
costs, and expenses (including reasonable attorneys' fees) arising from or related to
Licensee's use of the Software.
7.2 No Licensor Indemnity. Licensor shall have no obligation to indemnify Licensee
under any circumstances.

Section 8 — Confidentiality
8.1 Each party agrees to keep confidential all non-public information received from
the other party during the term of this Agreement.
8.2 Survival. Confidentiality obligations survive termination for two (2) years.

Section 9 — Warranty Disclaimer
THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.
LICENSOR DISCLAIMS ALL WARRANTIES INCLUDING MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE.

Section 10 — Governing Law
This Agreement shall be governed by and construed in accordance with the laws of the
State of New York. Any disputes shall be resolved exclusively in the state or federal
courts located in Manhattan, New York.

Section 11 — Entire Agreement
This Agreement constitutes the entire agreement between the parties.

IN WITNESS WHEREOF, the parties have executed this Agreement.

Omega Systems Inc.                  Sigma Analytics Ltd.
By: ___________________             By: ___________________
Name: David Chen, President         Name: Emily Brooks, CTO
Date: March 1, 2025                 Date: March 1, 2025
""",
)


# ---------------------------------------------------------------------------
# Contract 3 — Indian Employment Bond (enforceability test)
# ---------------------------------------------------------------------------
CONTRACT_DELTA_EPSILON = SyntheticContract(
    contract_id="eval_delta_epsilon_003",
    filename="Delta_Epsilon_Employment_Bond.pdf",
    title="Delta–Epsilon Employment Bond Agreement",
    jurisdiction="Maharashtra, India",
    description="An employment bond with ₹2,00,000 penalty clause and 2-year lock-in, raising Indian enforceability questions.",
    present_clauses={
        "Termination": ["Clause 4 — Early Exit"],
        "Payment": ["Clause 3 — Bond Amount"],
        "Confidentiality": ["Clause 6 — Confidentiality"],
        "Dispute Resolution": ["Clause 8 — Jurisdiction"],
    },
    absent_clauses=["Indemnification", "Liability Limits", "Automatic Renewal", "Data Protection"],
    conflicting_clauses=[],
    full_text="""EMPLOYMENT BOND AGREEMENT

This Employment Bond Agreement ("Bond") is executed on June 10, 2025,
by and between Delta Technologies Pvt. Ltd., a company incorporated under the
Companies Act, 2013, having its registered office in Pune, Maharashtra ("Company"),
and Mr. Arjun Sharma, residing at Flat 204, Kothrud, Pune ("Employee").

WHEREAS the Company is providing specialised training and proprietary knowledge
to the Employee at significant cost to the Company;

NOW THEREFORE, in consideration of the training and employment opportunity, the
parties agree as follows:

Clause 1 — Employment
The Company agrees to employ the Employee as a Senior Software Engineer in the
Artificial Intelligence division, commencing from July 1, 2025.

Clause 2 — Training Period
The Company shall provide the Employee with intensive training on proprietary AI/ML
systems during the first six (6) months of employment at an estimated training cost
of ₹4,50,000 (Rupees Four Lakhs Fifty Thousand).

Clause 3 — Bond Amount and Lock-in Period
3.1 Lock-in Period. The Employee agrees to serve the Company for a minimum period
of two (2) years from the date of completion of training ("Lock-in Period").
3.2 Bond Penalty. If the Employee voluntarily resigns or abandons employment before
the expiry of the Lock-in Period, the Employee shall pay the Company a bond penalty
of ₹2,00,000 (Rupees Two Lakhs) as liquidated damages representing a reasonable
pre-estimate of the Company's training investment loss.
3.3 Pro-rata Reduction. The bond penalty shall be reduced pro-rata for each completed
month of service after the training period.

Clause 4 — Early Exit
4.1 Notice Period. Either party may terminate employment by providing ninety (90)
calendar days prior written notice or salary in lieu thereof.
4.2 Company Termination. The Company may terminate the Employee's employment
immediately for misconduct, dishonesty, or material breach of Company policies,
in which case the bond penalty shall not apply.

Clause 5 — Intellectual Property
All inventions, code, and proprietary developments created during employment belong
exclusively to the Company.

Clause 6 — Confidentiality
6.1 The Employee shall not disclose any proprietary information, trade secrets, client
data, or business strategies learned during employment.
6.2 This obligation survives termination indefinitely.

Clause 7 — Non-Compete
The Employee agrees not to join any direct competitor of the Company for a period of
twelve (12) months following termination of employment within India.

Clause 8 — Jurisdiction and Dispute Resolution
8.1 Governing Law. This Bond shall be governed by the laws of India.
8.2 Jurisdiction. Any dispute arising out of this Bond shall be subject to the exclusive
jurisdiction of the courts in Pune, Maharashtra.

Clause 9 — Entire Agreement
This Bond constitutes the entire agreement between the parties regarding the
subject matter hereof.

IN WITNESS WHEREOF:

Delta Technologies Pvt. Ltd.        Employee
By: ___________________              Signature: ___________________
Name: Priya Deshmukh, HR Director   Name: Arjun Sharma
Date: June 10, 2025                  Date: June 10, 2025
""",
)


# ---------------------------------------------------------------------------
# Contract 4 — Supply Agreement with Conflicting Clauses
# ---------------------------------------------------------------------------
CONTRACT_GREENLEAF_TERRA = SyntheticContract(
    contract_id="eval_greenleaf_terra_004",
    filename="GreenLeaf_TerraCo_Supply.pdf",
    title="GreenLeaf–TerraCo Supply Agreement",
    jurisdiction="England and Wales",
    description="A supply agreement containing internal contradictions in termination and payment provisions.",
    present_clauses={
        "Termination": ["Section 7 — Termination", "Section 12 — Exit Provisions"],
        "Indemnification": ["Section 9 — Indemnification"],
        "Liability Limits": ["Section 10 — Liability"],
        "Payment": ["Section 4 — Payment", "Section 11 — Financial Provisions"],
        "Confidentiality": ["Section 8 — Confidentiality"],
        "Dispute Resolution": ["Section 13 — Governing Law"],
    },
    absent_clauses=["Automatic Renewal", "Data Protection"],
    conflicting_clauses=["Termination", "Payment"],
    full_text="""SUPPLY AGREEMENT

This Supply Agreement ("Agreement") is made on August 20, 2025,
BETWEEN: GreenLeaf Organics PLC, registered in England ("Buyer"),
AND: TerraCo Agricultural Supplies Ltd., registered in Wales ("Supplier").

Section 1 — Supply Obligations
Supplier shall deliver organic fertiliser products as specified in Purchase Orders
issued by Buyer under this Agreement.

Section 2 — Quality Standards
All products must conform to UK organic certification standards (Soil Association) and
Buyer's quality specifications attached as Schedule A.

Section 3 — Delivery
3.1 Delivery shall be DDP (Delivered Duty Paid) to Buyer's distribution centres.
3.2 Delivery timelines per Purchase Order. Late deliveries exceeding ten (10) business
days entitle Buyer to cancel the relevant Purchase Order.

Section 4 — Payment
4.1 Payment Terms. Buyer shall pay all undisputed invoices within forty-five (45) days
of receipt of goods and a valid invoice ("Net 45").
4.2 Early Payment Discount. A two percent (2%) discount applies for payments made
within ten (10) days.
4.3 Disputed Invoices. Buyer must notify Supplier of disputed amounts within twenty
(20) days of invoice receipt.

Section 5 — Term
This Agreement has an initial term of three (3) years from the Effective Date.

Section 6 — Representations
Supplier represents and warrants that all products comply with applicable UK health
and safety regulations.

Section 7 — Termination
7.1 Termination for Convenience. Either party may terminate by providing thirty (30)
calendar days written notice.
7.2 Termination for Cause. Either party may terminate immediately if the other
commits a material breach and fails to cure within fourteen (14) days.

Section 8 — Confidentiality
Each party shall maintain the confidentiality of the other party's business information.
Confidentiality obligations survive for five (5) years after termination.

Section 9 — Indemnification
9.1 Supplier shall indemnify Buyer for any product liability claims arising from
defective or non-conforming goods.
9.2 Each party indemnifies the other for claims arising from its negligence.

Section 10 — Liability
10.1 Liability Cap. Each party's total aggregate liability under this Agreement shall
not exceed the total fees paid during the preceding six (6) months.
10.2 Exclusion. Neither party shall be liable for loss of profits, business interruption,
or indirect damages.

Section 11 — Financial Provisions
NOTICE: THE FOLLOWING FINANCIAL PROVISIONS WERE ADDED BY AMENDMENT DATED
OCTOBER 1, 2025 AND SUPPLEMENT SECTION 4.
11.1 Extended Payment Terms. Notwithstanding Section 4.1, for orders exceeding
£50,000, Buyer shall pay within ninety (90) days of delivery ("Net 90").
11.2 Interest on Overdue Amounts. Overdue amounts accrue interest at 3% per annum
above the Bank of England base rate.

Section 12 — Exit Provisions
NOTICE: THE FOLLOWING EXIT PROVISIONS WERE ADDED BY AMENDMENT AND
SUPPLEMENT SECTION 7.
12.1 Termination Notice Period. Notwithstanding Section 7.1, either party must provide
a minimum of one hundred and eighty (180) calendar days written notice for
termination for convenience.
12.2 Transition Assistance. Upon notice of termination, Supplier shall provide
reasonable transition assistance for up to ninety (90) days.

Section 13 — Governing Law
13.1 This Agreement is governed by the laws of England and Wales.
13.2 Disputes shall be resolved by arbitration under the LCIA Rules in London.

Section 14 — Entire Agreement
This Agreement, as amended, constitutes the entire agreement between the parties.

IN WITNESS WHEREOF:

GreenLeaf Organics PLC               TerraCo Agricultural Supplies Ltd.
By: ___________________               By: ___________________
Name: Sarah Collins, Procurement Dir  Name: Gareth Owen, CEO
Date: August 20, 2025                 Date: August 20, 2025
""",
)


# ---------------------------------------------------------------------------
# Contract 5 — Data Processing Agreement (GDPR/CCPA heavy)
# ---------------------------------------------------------------------------
CONTRACT_NOVAHEALTH_MEDICORE = SyntheticContract(
    contract_id="eval_novahealth_medicore_005",
    filename="NovaHealth_MediCore_DPA.pdf",
    title="NovaHealth–MediCore Data Processing Agreement",
    jurisdiction="Ireland (EU)",
    description="A data-heavy DPA with extensive GDPR/CCPA compliance provisions.",
    present_clauses={
        "Termination": ["Article 10 — Term and Termination"],
        "Indemnification": ["Article 8 — Indemnification"],
        "Liability Limits": ["Article 9 — Limitation of Liability"],
        "Confidentiality": ["Article 6 — Confidentiality"],
        "Payment": ["Article 3 — Fees"],
        "Data Protection": ["Article 4 — Data Processing Obligations", "Article 5 — Security"],
        "Dispute Resolution": ["Article 12 — Governing Law"],
    },
    absent_clauses=["Automatic Renewal"],
    conflicting_clauses=[],
    full_text="""DATA PROCESSING AGREEMENT

This Data Processing Agreement ("DPA") is entered into as of September 1, 2025,
by and between NovaHealth Systems Ltd., an Irish company ("Controller"),
and MediCore Cloud Services Inc., a US corporation ("Processor").

Article 1 — Purpose
This DPA governs the processing of personal data by Processor on behalf of
Controller in connection with the provision of cloud-based electronic health
record (EHR) management services.

Article 2 — Definitions
"Personal Data" means any information relating to an identified or identifiable
natural person as defined under GDPR Article 4(1) and CCPA Section 1798.140(v).
"Special Category Data" includes health data, genetic data, and biometric data.

Article 3 — Fees
3.1 Processing Fees. Controller shall pay Processor a monthly processing fee of
€25,000 for hosting and managing up to 500,000 patient records.
3.2 Invoicing. Processor shall issue invoices on the first business day of each
month for the preceding month's services.
3.3 Payment Terms. Invoices are payable within sixty (60) days of receipt ("Net 60").

Article 4 — Data Processing Obligations
4.1 Lawful Basis. Processor shall process Personal Data only on documented
instructions from Controller, unless required by EU or Member State law.
4.2 Data Minimisation. Processor shall process only the minimum Personal Data
necessary to perform the services.
4.3 Sub-processors. Processor shall not engage any sub-processor without prior
specific written authorisation from Controller. A list of approved sub-processors
is attached as Annex B.
4.4 Cross-border Transfers. Any transfer of Personal Data outside the European
Economic Area ("EEA") shall be subject to Standard Contractual Clauses (SCCs)
or an equivalent safeguard approved by the European Commission.
4.5 Data Subject Rights. Processor shall assist Controller in fulfilling data subject
access, rectification, erasure, and portability requests within ten (10) business days.

Article 5 — Security Measures
5.1 Processor shall implement appropriate technical and organizational measures
including: encryption (AES-256) at rest and in transit (TLS 1.3), access controls,
regular penetration testing, and SOC 2 Type II compliance.
5.2 Breach Notification. Processor shall notify Controller of any personal data breach
without undue delay and in any event within thirty-six (36) hours of becoming aware
of the breach, including: (a) nature of the breach, (b) categories and approximate
number of data subjects affected, (c) likely consequences, and (d) measures taken.

Article 6 — Confidentiality
6.1 Processor shall ensure that personnel authorised to process Personal Data have
committed to confidentiality obligations.
6.2 Confidentiality obligations survive termination of this DPA indefinitely for
health data and Special Category Data.

Article 7 — Audit Rights
7.1 Controller shall have the right to audit Processor's compliance with this DPA,
upon reasonable notice, no more than twice per calendar year.
7.2 Processor shall make available all information necessary to demonstrate compliance
with GDPR Article 28 obligations.

Article 8 — Indemnification
8.1 Mutual Indemnity. Each party shall indemnify the other against fines, penalties,
and damages arising from its breach of this DPA or applicable data protection laws.
8.2 Uncapped for Wilful Breach. Indemnification obligations for wilful or grossly
negligent data breaches are not subject to the cap in Article 9.

Article 9 — Limitation of Liability
9.1 Aggregate Cap. Subject to Article 8.2, each party's total aggregate liability
shall not exceed €1,500,000 or the total fees paid during the preceding twenty-four
(24) months, whichever is greater.
9.2 Consequential Damages. Neither party shall be liable for indirect, incidental,
or consequential damages, except in connection with breaches of Article 4 (Data
Processing Obligations) or Article 6 (Confidentiality).

Article 10 — Term and Termination
10.1 Term. This DPA shall remain in effect for the duration of the underlying
EHR services agreement.
10.2 Termination for Breach. Either party may terminate this DPA upon sixty (60)
days written notice if the other party commits a material breach that is not cured
within thirty (30) days of written notice.
10.3 Data Return and Deletion. Upon termination, Processor shall, at Controller's
election, return all Personal Data in a standard machine-readable format or securely
delete it using NIST SP 800-88 compliant methods within forty-five (45) days.

Article 11 — Data Protection Impact Assessments
Processor shall provide reasonable assistance to Controller in conducting Data
Protection Impact Assessments (DPIAs) as required under GDPR Article 35.

Article 12 — Governing Law and Dispute Resolution
12.1 This DPA is governed by the laws of Ireland.
12.2 Disputes shall first be escalated to senior executives for good-faith resolution
over thirty (30) days. Unresolved disputes shall be submitted to the courts of Dublin.

Article 13 — Miscellaneous
This DPA supplements and forms part of the underlying services agreement.

IN WITNESS WHEREOF:

NovaHealth Systems Ltd.              MediCore Cloud Services Inc.
By: ___________________               By: ___________________
Name: Dr. Aoife Murphy, DPO          Name: Kevin Rodriguez, VP Legal
Date: September 1, 2025               Date: September 1, 2025
""",
)


# ---------------------------------------------------------------------------
# Convenience exports
# ---------------------------------------------------------------------------

ALL_CONTRACTS: List[SyntheticContract] = [
    CONTRACT_ACME_BETA,
    CONTRACT_OMEGA_SIGMA,
    CONTRACT_DELTA_EPSILON,
    CONTRACT_GREENLEAF_TERRA,
    CONTRACT_NOVAHEALTH_MEDICORE,
]

CONTRACT_BY_ID: Dict[str, SyntheticContract] = {c.contract_id: c for c in ALL_CONTRACTS}
