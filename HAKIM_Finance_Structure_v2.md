# HAKIM Personal Finance — Firefly III Structure v2 (BUILD VERSION)
_6 Sep 2026. Supersedes v1. Incorporates all of Hisham's Money Pro screenshots and
corrections. This is the document the Claude Code brief implements._

## Design rules
1. **Categories = WHAT** the money bought. Never who, never where.
2. **Tags = WHO + CONTEXT.** Money Pro's "Agent" (Adam/Aser/Hisham/Sarah) → person tags.
   Money Pro's "Class" (Online/Home/House finishing/Business…) → context tags. Same
   concepts Hisham already used, now on one transaction together.
3. **Accounts track money that returns** (lending/debt) — Hisham's "Lending & refund"
   trick, done natively.
4. **Bills = everything recurring.** Firefly auto-matches payments; feeds forecasts and
   expiry alerts.
5. **Transfers are never income or expense.** Account→account moves (incl. paying credit
   cards, funding trading, Sarah↔Hisham) are transfers — the thing Hisham loved in Money Pro.
6. Anything unclear → category **To review**, checked weekly.
7. **One-system-per-domain**: Firefly = personal/household only. MENTCO→ERPNext,
   trading→HISSAR, factory→its own books. Cross-entity money appears here only as
   income/transfer categories.

---

## ACCOUNTS — exact list, taken as-is from Money Pro (nothing erased)
All opening balances are entered FRESH from bank apps on build day. Money Pro balances
are stale and are NOT migrated.

### Asset accounts — SAR unless noted
**Cash & safes:** Hisham Wallet (SAR) · Sarah's wallet (SAR) · Safe (SAR) ·
Safe Dollar (USD) · Adam safe (SAR, savings) · Aser safe (SAR, savings) ·
Egyptian pound safe (EGP) · UAE Dirham (AED)

**Banks — Saudi (SAR):** Hisham SNB main · Hisham SNB saving · Sarah SNB main ·
Sarah SNB shopping · Sarah SNB saving · SABB main · SABB Hisham shopping ·
SABB School · SABB Travel
(NCB = SNB after the merger; named SNB going forward, as in the bank app.)

**Banks — Egypt:** Bank Misr USD · Bank Misr EGP
**Digital wallets (SAR):** STC Pay · D360 · Barq

**Receivables:** "Owed to me (مستحقات)" (SAR asset) — replaces the "Lending & refund"
account. Front money for someone → split: real expense part + transfer here, tagged
with the person. Repayment = transfer back. Net position + ageing per person.

### Liability accounts
Credit cards: SABB Alfursan •4331 · SABB Mastercard •1437 · SABB Visa •5019 ·
Hisham SNB Alfursan •0756 · Hisham SNB Mastercard •9xxx · Sarah SNB Mastercard •437x
Plus "I owe (عليّ)" — personal debts to people.

Card spending = withdrawal from the card (expense + debt grows in one entry).
Card payment = transfer bank→card.

**Security rule:** full card numbers + expiry dates live in Vaultwarden only. The ledger
uses last-4 names. IBANs may sit in Firefly account notes (local instance).

### Currencies
Enable SAR (default), EGP, USD, AED. Each account holds its own currency natively.

---

## TRANSACTION TYPES (Money Pro's 7 → Firefly's 3)
- Expense → **Withdrawal** · Income → **Deposit** · Money Transfer → **Transfer**
- Liability Acquisition / Discharge → implied by using a liability account.
- Asset Purchase / Sale → out of scope by doctrine (investments = HISSAR domain).
- Plus native **opening balance** and **reconciliation**.
- **Attachments:** receipt photo / PDF on any transaction, stored locally.

---

## EXPENSE CATEGORIES (21 + utility buckets)
Groceries & supermarket · Eating out & delivery · Personal care ·
Clothing & accessories · Electronics & gadgets · Entertainment & outings ·
Sports & fitness · Subscriptions & digital · Utilities & telecom · Home & maintenance ·
Household staff · Car · Transport & taxis · Medical & pharmacy · School & education ·
Government & documents · Travel · Gifts & occasions · Hajj & Umrah (حج وعمرة) ·
Zakat & charity (زكاة وصدقة) · Insurance · Bank & fees · To review

**The work rule:** work expenses Hisham pays from his pocket are REAL personal expenses
in their normal categories, tagged `work`. If MENTCO later repays one, that repayment
books as income category "Reimbursements".

## INCOME CATEGORIES (7)
Business income (MENTCO salary/drawings) · Salary & allowances · Rental income ·
Interest income · Gifts received · Reimbursements · Other income
**Transfers, not income:** trading in/out (HISSAR), factory capital contribution,
Sarah↔Hisham moves. **Killed:** Credit card pay (→ transfer), Refund (→ deposit into
original expense category).

## TAGS
People: `Hisham` `Sarah` `Aser` `Adam` `Family` `Maid` `Driver`
Context: `online` `luxury` `home-project` `work` `trip:<name>`
Allowance detail: `allowance:housing` `allowance:tickets`

## BILLS REGISTER (auto-match + forecast + expiry alerts)
Streaming ×6 · Microsoft · VPN · STC lines ×3 · Utilities (electricity/water/internet/gas)
· Maid salary · School installments · Insurance policies · Government renewals per person
(iqama, passport, exit-reentry — with due dates) · Rent (pending own-vs-rent).

## REPORTS
Native: Income/Expenses, Assets/Liabilities (net worth), Debt Balance, Transactions,
Cash Flow. NOT native: Projected Balance → Finance agent capability (cash-flow forecast
over the bills register).

## CONFIRM ON BUILD DAY (defaults chosen, build not blocked)
1. Rent or own home? (if rent → Bill)
2. Arabic in UI: DEFAULT = English names, Arabic labels in the two receivable/debt
   accounts only; the agent speaks Arabic on request regardless.
3. Zakat & charity separate from Hajj & Umrah — confirm.
4. A 7th credit card was possibly visible in Money Pro — confirm only 6 exist.
5. Exact last-4 for the two SNB cards.
