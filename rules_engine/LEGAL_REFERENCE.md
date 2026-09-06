# Legal Metrology (Packaged Commodities) Rules, 2011 — Reference Notes

Compiled for: Anshi (Rules Research) → handed off as the reference the
code in `rules_engine/checker.py` is built against.

Source: https://consumeraffairs.gov.in/pages/legal-metrology-act,
Rule 6 & Rule 7 of the LMPC Rules, 2011, and official FAQs issued by the
Dept. of Consumer Affairs, Legal Metrology Division.

**Important caveat:** These Rules have been amended multiple times (2017
country-of-origin insertion, 2017 font-size table substitution, a 2026
e-commerce amendment, etc.). The values below reflect the most commonly
cited/consolidated text. Before final submission, do a last-minute check
against the current consolidated text on indiacode.nic.in — and it's
fine (even expected) to state this as a known limitation in your PPT.

---

## 1. Font size thresholds (Rule 7(2) + Table-I)

Table-I applies when net quantity is declared by **weight or volume**
(the common case — g/kg, ml/l). It specifies the minimum height of the
**numeral** only (not surrounding letters/prefixes):

| Net Quantity Range | Min height — normal case | Min height — if blown/formed/molded/embossed/perforated |
|---|---|---|
| Up to 200 g/ml | 1 mm | 2 mm |
| Above 200 g/ml, up to 500 g/ml | 2 mm | 4 mm |
| Above 500 g/ml | 4 mm | 6 mm |

There is a separate **Table-II** for quantity declared in length/area/number
(not weight/volume) — not implemented in the code yet since most packaged
commodities use weight/volume, but worth adding if your test products
include anything measured by length or count.

**Rule 7(3)** — general (non-numeral) letters anywhere in a declaration:
minimum 1mm height (2mm if blown/formed/molded/embossed/perforated).

**Important nuance (per official FAQ Q.45):** the numeral-height rule
applies **only to the MRP value itself** (e.g. the "120" in "MRP Rs
120"), NOT to the prefix "MRP Rs." or the suffix "Inclusive of all
taxes" — those only need the general 1mm letter-height minimum.

**Width rule (Rule 7(3) proviso):** width of any letter/numeral must be
at least 1/3 of its height (except numeral "1" and letters i, I, l).

---

## 2. Exact wording required for MRP

- Rule 6(1)(f): retail sale price must be declared, **inclusive of all taxes**
- Per official FAQ (Q.44): the letter case for "inclusive of all taxes"
  may be **upper case, lower case, OR sentence case** — no specific case
  is mandated
- Practical formats seen: "MRP Rs. 120 (Inclusive of all taxes)" or
  "MRP ₹120 Incl. of all taxes" — no single rigid phrase-format is
  prescribed beyond the substance of the words

---

## 3. Net quantity — valid units & rules

- Must be declared in the **standard unit of weight** (g, kg) or
  **measure/volume** (ml, l), or as a **count** if sold by number
- Rule 4(1): the weight of wrappers/packaging materials must be
  EXCLUDED from the declared net quantity (only the commodity itself
  counts)
- Vague qualifiers like "approx," "approximately," or "around" attached
  to the quantity are **not compliant** — the Numeration Rules require
  exact values, not ranges/approximations
- No specific universal decimal-precision rule was found in the sources
  reviewed — if this matters for your rules engine, flag it as an open
  item rather than guessing a number

---

## 4. Manufacturer / Packer / Importer info requirements

- Rule 6(1)(a): name & address of the **manufacturer**
- If the manufacturer is not the packer: name & address of **both**
  manufacturer and packer
- For **imported** packages: name & address of the **importer** is
  required — per official FAQ, this alone (plus Country of Origin) is
  sufficient; the foreign manufacturer's address is NOT required
- **Explanation I to Rule 6(1)(a):** if a name/address appears WITHOUT
  qualifying words like "manufactured by" or "packed by," it is
  **presumed** to be the manufacturer's — so a bare company block can
  still be valid, just ambiguous to an automated checker
- Common valid phrasings seen: "Manufactured by," "Marketed by,"
  "Packed by," "Imported by" — "Marketed by [Brand Owner]" alone has
  also been confirmed sufficient per official FAQ (Q.12)

---

## 5. Consumer care requirement

- **Rule 6(2)**: every package must bear the **name, address, telephone
  number, AND e-mail address** of the person/office to contact for
  consumer complaints — technically all four fields are required
- In practice, per official guidance, the most commonly cited real-world
  violation is a **non-functional phone number or missing email** — so
  these two are the highest-priority fields to check for
- No specific mandated format for the phone/email themselves (beyond
  being genuine/functional) was found in the sources reviewed

---

## 6. Country of origin

- **Rule 6(1)(aa)** (inserted 2017): country of origin/manufacture/
  assembly is mandatory **only for imported products**
- Domestic (India-manufactured) products are **NOT required** to
  declare this (confirmed by official FAQ), though some choose to
  voluntarily (e.g. "Made in India")
- Accepted format: **"Made in [Country]"**
- Note: a 2026 e-commerce amendment reportedly strengthens Country of
  Origin display requirements specifically for **online marketplace
  listings** — if your project's scope touches e-commerce listings
  (not just physical labels), this may need separate handling; verify
  against the current amendment text if relevant to your submission

---

## 7. Exemptions (Rule 3 & Rule 26)

Products/situations where these mandatory declarations **do not apply
at all** — worth stating explicitly as a known limitation, since an
automated image-based checker cannot verify most of these on its own
(e.g. it can't confirm a buyer is an "industrial consumer" or weigh the
actual product):

- Packages sold by weight/measure of **10g/10ml or less** (except
  tobacco) — exempt from Unit Sale Price declaration specifically
- **Fast food** packed by a hotel/restaurant/similar body for direct
  sale to the consumer
- **Scheduled and non-scheduled drugs** covered under the Drugs (Price
  Control) Order, 1995
- **Agricultural farm produce** in packages above 50 kg
- **Thread** sold in coil form to handloom weavers
- Packages **above 25 kg/25 litre** (50 kg/litre for cement &
  fertilizer specifically) — exempt from these particular retail
  package declaration requirements
- **Institutional/industrial packages**, provided they are clearly and
  prominently marked **"Not for Retail Sale"**

---

## Still open / needs verification before final submission

- [ ] Table-II (quantity declared by length/area/number) — not yet
      implemented, only needed if test products include such items
- [ ] Exact decimal-precision rule for net quantity, if any
- [ ] Re-verify all values against the current consolidated Rules text
      on indiacode.nic.in, since multiple amendments exist
- [ ] The 2026 e-commerce amendment's country-of-origin requirements,
      if in scope for this project
