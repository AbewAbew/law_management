# Law Management App - User Guide

## Billing Workflows
This guide explains how to handle different billing scenarios in the Law Management App.

### 1. Flat Fee Billing 🏷️
Used when a fixed price is agreed upon for the entire case.

#### Option A: Upfront Payment
*   **Scenario:** Client pays the full amount before work begins.
*   **Setup:**
    1.  Set **Billing Type** to `Flat Fee`.
    2.  Set **Payment Structure** to `Upfront`.
    3.  Enter the **Total Fee** (e.g., 50,000 ETB).
*   **Workflow:**
    1.  Finance User clicks **"Create Invoice"**.
    2.  System generates an invoice for the full amount.
    3.  Once paid, Finance marks the Case as `Active`.

#### Option B: Milestone-Based
*   **Scenario:** Client pays in installments based on progress (e.g., "Drafting", "Filing", "Hearing").
*   **Setup:**
    1.  Set **Payment Structure** to `Milestones`.
    2.  Fill the **Milestones Table** (Name, Amount, Due Date).
*   **Workflow:**
    1.  **Lawyer:** When a stage is done, open the Case and change that Milestone's status to **"Ready to Bill"**.
    2.  **Finance:** Clicks **"Create Milestone Invoice"**.
    3.  System bundles all "Ready to Bill" items into one invoice and updates their status to "Invoiced".

#### Option C: Completion
*   **Scenario:** Client pays only after the case is finished.
*   **Setup:** Set **Payment Structure** to `Completion`.
*   **Workflow:** Same as Upfront, but usually triggered at the end of the case.

---

### 2. Hourly Billing ⏳
Used when billing is based on time spent.

*   **Setup:**
    1.  Set **Billing Type** to `Hourly`.
    2.  Set the **Hourly Rate** in the Case settings (or rely on individual Lawyer rates).
*   **Tracking Time:**
    1.  Lawyers create **Timesheets**.
    2.  **Crucial:** In the Timesheet Detail, they must select the **Case**.
    3.  *Smart Feature:* The system will automatically fetch that Lawyer's specific rate for that Case.
*   **Billing:**
    1.  Finance clicks **"Create Invoice"**.
    2.  System finds all **Unbilled & Approved** timesheets for this Case.
    3.  Generates a detailed invoice listing every activity.

---

### 3. Retainer Billing 🏦
Used when the client deposits a lump sum, and work draws down from it.

*   **Setup:**
    1.  Set **Billing Type** to `Retainer`.
    2.  Enter **Initial Retainer Amount** (e.g., 100,000 ETB).
*   **Step 1: The Deposit**
    1.  Finance clicks **"Create Invoice"**.
    2.  System bills the Initial Retainer Amount immediately.
*   **Step 2: The Usage**
    1.  Lawyers log time via **Timesheets** (just like Hourly billing).
    2.  These timesheets are tracked against the case to calculate the remaining balance.

---

### 4. Contingency Billing ⚖️
Used when the fee is a percentage of the money won (Settlement).

*   **Setup:**
    1.  Set **Billing Type** to `Contingency`.
    2.  Enter **Percentage of Recovery** (e.g., 20%).
*   **Workflow:**
    1.  Win the case! 🏆
    2.  Enter the **Settlement Amount** (e.g., 1,000,000 ETB).
    3.  Click **"Calculate Contingency Fee"**.
    4.  System shows a confirmation: *"Fee is 200,000 ETB (20%). Create Invoice?"*
    5.  Click **Yes** to generate the invoice.

---

## Permissions & Security 🛡️
The system now enforces strict access controls based on roles and team membership.

### 1. Case Visibility
*   **Partners & System Managers:** Have full access to **ALL** cases in the system.
*   **Associates & Paralegals:** Can **ONLY** see cases where they are explicitly listed in the **Team Members** table. If they are removed from the team, they lose access to the case.

### 2. Case Creation
*   **Paralegals:** Do **NOT** have permission to create new Cases. They can only view and work on cases assigned to them.
*   **Partners & Associates:** Can create new cases.

### 3. Task Assignment
*   **Multi-User Assignment:** You can now assign a Task to **multiple** people using the **"Assignees"** field.
*   **Team-Only Filter:** When you click the "Assignees" dropdown, the list is strictly filtered to show **ONLY** the members of the selected Case's team.
*   **Assigned To (Sidebar):** The **"Assigned To"** button in the left sidebar is also filtered. When adding a ToDo from the sidebar, you will only see Case Members in the user list.
*   **Safety:** This ensures you cannot accidentally assign confidential case tasks to unauthorized staff.
