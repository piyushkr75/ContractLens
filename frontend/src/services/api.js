const BASE_URL = import.meta.env.VITE_API_URL || '';

export const api = {
  /**
   * Check backend server health and in-memory stats
   */
  async getHealth() {
    const res = await fetch(`${BASE_URL}/api/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  /**
   * Upload contract file (PDF, DOCX, TXT)
   */
  async uploadContract(file) {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${BASE_URL}/api/contracts/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Contract upload failed');
    }
    return res.json();
  },

  /**
   * Upload synthetic sample contract as text file
   */
  async uploadTextContract(filename, textContent) {
    const blob = new Blob([textContent], { type: 'text/plain' });
    const file = new File([blob], filename, { type: 'text/plain' });
    return this.uploadContract(file);
  },

  /**
   * List all in-memory contracts
   */
  async listContracts() {
    const res = await fetch(`${BASE_URL}/api/contracts`);
    if (!res.ok) throw new Error('Failed to fetch contracts');
    return res.json();
  },

  /**
   * Get single contract detail
   */
  async getContract(contractId) {
    const res = await fetch(`${BASE_URL}/api/contracts/${contractId}`);
    if (!res.ok) throw new Error('Failed to fetch contract');
    return res.json();
  },

  /**
   * Delete contract from memory & local storage
   */
  async deleteContract(contractId) {
    const res = await fetch(`${BASE_URL}/api/contracts/${contractId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete contract');
    return res.json();
  },

  /**
   * Run or retrieve risk intelligence analysis with optional custom review policy
   */
  async analyzeContract(contractId, reviewPolicy = null) {
    const res = await fetch(`${BASE_URL}/api/contracts/${contractId}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ review_policy: reviewPolicy }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Analysis request failed');
    }
    return res.json();
  },

  /**
   * Retrieve all indexed FAISS chunks with page numbers and section headers
   */
  async getContractChunks(contractId) {
    const res = await fetch(`${BASE_URL}/api/contracts/${contractId}/chunks`);
    if (!res.ok) throw new Error('Failed to retrieve contract chunks');
    return res.json();
  },

  /**
   * Get URL to download/preview original document
   */
  getContractDownloadUrl(contractId) {
    return `${BASE_URL}/api/contracts/${contractId}/download`;
  },

  /**
   * Conversational RAG with FAISS in-memory vector index and optional MCP legal search
   */
  async chatWithContract(contractId, message, history = [], topK = 4, researchMode = 'auto') {
    const res = await fetch(`${BASE_URL}/api/contracts/${contractId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        history,
        top_k: topK,
        research_mode: researchMode,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Chat query failed');
    }
    return res.json();
  },

  /**
   * Check MCP server status, active transport, and discovered research tools
   */
  async getMcpStatus() {
    const res = await fetch(`${BASE_URL}/api/mcp/status`);
    if (!res.ok) throw new Error('Failed to retrieve MCP status');
    return res.json();
  },

  /**
   * Compare two contracts loaded in the in-memory session
   */
  async compareContracts(contractAId, contractBId, focusCategories = null) {
    const res = await fetch(`${BASE_URL}/api/contracts/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contract_a_id: contractAId,
        contract_b_id: contractBId,
        focus_categories: focusCategories,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Contract comparison failed');
    }
    return res.json();
  },
};


export const SAMPLE_CONTRACT = `MASTER SERVICES AGREEMENT (ENTERPRISE MSA)

This Master Services Agreement is entered into by and between Enterprise Cloud Inc. ("Customer") and DevTech Solutions LLC ("Provider").

ARTICLE 1. SERVICES & DELIVERABLES
Provider shall perform software engineering, architecture, and cloud migration services described in Statements of Work. All intellectual property, discoveries, software code, tools, and background frameworks developed or utilized by Provider shall be deemed "Work Made for Hire" and the exclusive, perpetual property of Customer from inception without reservation.

ARTICLE 2. INDEMNIFICATION & LIABILITY
Provider shall defend, indemnify, and hold harmless Customer, its affiliates, directors, officers, and agents against ANY and all claims, liabilities, losses, damages, fines, and expenses (including full legal fees) arising directly or indirectly from Provider's performance, services, or alleged breach of any term of this Agreement.
Provider's indemnity obligations under this Section are uncapped, unlimited, and not subject to any limitation of liability or exclusion of consequential damages.

ARTICLE 3. LIMITATION OF LIABILITY
Customer's aggregate liability arising under or related to this Agreement for all causes of action shall in no event exceed the sum of $500. Under no circumstances shall Customer be liable for lost profits, indirect, punitive, or consequential damages. Provider waives all rights to claim damages against Customer.

ARTICLE 4. TERM AND TERMINATION
This Agreement commences on the Effective Date and continues for twenty-four (24) months.
4.1 Termination for Convenience: Customer may terminate this Agreement or any Statement of Work at any time, for any reason or no reason, upon three (3) calendar days written notice.
4.2 Provider Termination: Provider may not terminate this Agreement for convenience and must provide one hundred eighty (180) days notice in the event of an uncured material non-payment breach.

ARTICLE 5. NON-COMPETE & RESTRICTIVE COVENANTS
During the Term and for a period of five (5) years following termination or expiration, Provider and its employees shall not directly or indirectly provide software, IT consulting, or cloud services to any commercial entity globally operating in any industry that Customer serves or may foreseeably enter.

ARTICLE 6. PAYMENT TERMS & AUDIT RIGHTS
Customer will pay undisputed invoices within ninety (90) days of receipt. Customer reserves the right to audit Provider's internal servers, financial books, and source code repositories at any time without prior written notice to verify compliance.

ARTICLE 7. GOVERNING LAW & DISPUTE RESOLUTION
This Agreement is governed by the laws of the State of Delaware. Any dispute shall be settled by binding arbitration in Wilmington, Delaware, with each party bearing its own expenses. Provider waives all rights to participate in class actions or jury trials.
`;

export const SAMPLE_VENDOR_CONTRACT = `MASTER SAAS AGREEMENT (VENDOR FORM)

ARTICLE 1. TERMINATION
Vendor may terminate this agreement at any time for convenience upon thirty (30) days prior written notice.
Customer may terminate solely in the event of an uncured material breach by Vendor with thirty (30) days cure notice.

ARTICLE 2. PAYMENT TERMS
All invoices are payable Net 15 days from invoice date.
Late payments shall incur 1.5% monthly late interest fee on overdue charges.

ARTICLE 3. LIMITATION OF LIABILITY
Vendor's aggregate liability under this agreement shall in no event exceed the fees paid in the preceding three (3) months ($10,000 cap).
Neither party shall be liable for indirect, incidental, or consequential damages.

ARTICLE 4. INDEMNIFICATION
Customer agrees to defend and indemnify Vendor against all third-party claims arising from Customer data or IP infringement.
Vendor provides no indemnification to Customer under any circumstances.

ARTICLE 5. AUTOMATIC RENEWAL
This Agreement shall automatically renew for successive one (1) year terms unless either party provides written notice of non-renewal at least ninety (90) days prior to expiration.

ARTICLE 6. CONFIDENTIALITY
Mutual confidentiality obligations shall survive for a period of two (2) years following termination.

ARTICLE 7. DATA PROTECTION
Vendor will implement reasonable security standards. In the event of a security breach, Vendor will notify Customer within thirty (30) days.

ARTICLE 8. DISPUTE RESOLUTION & GOVERNING LAW
This agreement is governed by the laws of Delaware. All disputes shall be resolved through binding commercial arbitration in Wilmington, Delaware.
`;

export const SAMPLE_BUYER_CONTRACT = `ENTERPRISE SERVICES AGREEMENT (BUYER FORM)

SECTION 1. TERMINATION
Either party may terminate this agreement for convenience upon sixty (60) days prior written notice.
Either party may terminate for material breach with fifteen (15) days cure notice.

SECTION 2. PAYMENT TERMS
Invoices are payable on Net 60 days terms. No interest or late fees shall accrue on disputed or overdue amounts.

SECTION 3. LIMITATION OF LIABILITY
Each party's aggregate liability shall be capped at twelve (12) months fees or $500,000, whichever is greater.
The aggregate liability cap shall not apply to breaches of confidentiality, data protection obligations, or indemnification claims.

SECTION 4. INDEMNIFICATION
Mutual indemnification. Each party agrees to defend, indemnify, and hold harmless the other party from all third-party intellectual property infringement claims and gross negligence.

SECTION 5. TERM AND EXPIRATION
This agreement commences on the Effective Date and concludes after twelve (12) months of performance, after which this agreement shall permanently expire without automatic renewal.

SECTION 6. CONFIDENTIALITY
Proprietary information obligations shall survive for five (5) years following termination, and trade secrets shall be protected perpetually.

SECTION 7. DATA PROTECTION
Vendor shall strictly comply with GDPR and CCPA. Vendor must notify Customer of any data security breach within forty-eight (48) hours of discovery.

SECTION 8. DISPUTE RESOLUTION & GOVERNING LAW
This agreement shall be governed by the laws of California. Any legal action shall be brought exclusively in the state or federal courts in San Francisco, California.
`;

