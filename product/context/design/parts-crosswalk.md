---
artifact: parts-crosswalk
status: draft
authored-by: Service Designer (Moe)
last-revised: 2026-10-01
inputs: [engineering/client/src/components/, "@trussworks/react-uswds ^11.0.1 src/index.ts", "Figma: PA Compact Parts Library (USWDS Design Kit Beta 0.3)"]
see-also: [product/context/design/ui-workflow.md]
---

# Parts crosswalk: Figma Parts Library ↔ Trussworks ↔ our components

Which code part each Figma part matches. It does by hand what Figma Code Connect would do automatically (Focus is on the Pro plan, which doesn't include it). The same text is in each part's description in the Figma Parts Library, under "PA COMPACT CROSSWALK". Checked 2026-10-01 against `main` at `5593c40`.

## 1. Our app's pieces (what's built today)

| Our piece | Built from (Trussworks) | Figma kit piece | Note |
|---|---|---|---|
| `TextField` | `TextInput` + `Label` | Text input, Label | none |
| `SelectField` | `Select` + `Label` | Select, Label | none |
| `CountryField` | our `SelectField` | Select | none |
| `DatePickerField` | `DatePicker` + `Label` | Date picker | none |
| `DateFields` | `DateInput`, `DateInputGroup`, `FormGroup` | Memorable date page (no component set found) | Check the kit page |
| `FilePickerField` | `FileInput` + `Label` | File input | none |
| `DisplayField` | `Label` | Label | Read-only value display |
| `NameFields` | `Fieldset` + our `TextField` | Text input (no Fieldset piece in the kit) | none |
| `AddressFields` | `Fieldset` + our fields | Text input, Select | none |
| `FormStep` | `Button`, `Form`, `RequiredMarker` | Button, Label | **Doesn't use the Step indicator.** My earlier guess was wrong; checked 2026-10-01 |
| `Card` | **none: a custom box** (`bg-white padding-4 shadow-2 radius-lg`) | Card exists in the kit, but **isn't what our app uses** | **Departure from USWDS. Record as a design decision record** |
| `ProtectedRoute` | none (sign-in logic, no visual) | none | none |
| `app/page.tsx` | `Button` | Button | none |

## 2. Figma kit pieces and their code match

All have a Trussworks match unless marked. "Not used yet" means the app doesn't use it today.

| Kit piece | Trussworks | Used in our app? |
|---|---|---|
| Accordion | `Accordion` | No |
| Alert | `Alert` | No |
| Banner | `GovBanner` | No. **OPEN:** the Commission isn't a federal agency, so the federal banner may not apply |
| Breadcrumb | `Breadcrumb`, `BreadcrumbBar`, `BreadcrumbLink` | No |
| Button / Button big | `Button` (`size="big"`) | Yes (`FormStep`, home page) |
| Button group | `ButtonGroup` | No |
| Card | `Card` and its parts | No (see `Card` above) |
| Character count | `CharacterCount` | No |
| Checkbox | `Checkbox` | No |
| Collection | `Collection` and its parts | No |
| Combo box | `ComboBox` | No |
| Date picker / range | `DatePicker`, `DateRangePicker` | Yes (`DatePickerField`) |
| File input | `FileInput` | Yes (`FilePickerField`) |
| Footer | `Footer`, `FooterNav` | No |
| Header | `Header`, `PrimaryNav`, `ExtendedNav`, `NavMenuButton` | No |
| Icon list | `IconList` and its parts | No |
| Identifier | `Identifier` and its parts | No. **OPEN:** same federal question as the banner |
| In-page navigation | `InPageNavigation` | No |
| Input group, prefix/suffix | `InputGroup`, `InputPrefix`, `InputSuffix` | No |
| Label | `Label`, `RequiredMarker` | Yes (all field pieces) |
| Language selector | `LanguageSelector` | No |
| Modal | `Modal` and its parts | No |
| Pagination | `Pagination` | No |
| Process list | `ProcessList` and its parts | No |
| Radio buttons | `Radio` | No |
| Search | `Search` | No |
| Select | `Select` | Yes (`SelectField`) |
| Side navigation | `SideNav` | No |
| Site alert | `SiteAlert` | No |
| Step indicator | `StepIndicator`, `StepIndicatorStep` | No |
| Table | `Table` | No. See gap 1: what state staff need is open, so it isn't assumed to be a big table |
| Tag | `Tag` | No |
| Text area | `Textarea` | No |
| Text input | `TextInput` | Yes (`TextField`) |
| Time picker | `TimePicker` | No |
| Tooltip | `Tooltip` | No |
| Prose (headings) | none (a CSS class) | none |
| Link | `Link` | No |

## 3. In code but not in the Figma kit

`Fieldset`, `Form`, `FormGroup`, `ErrorMessage`, `TextInputMask`, `ValidationChecklist`, `MegaMenu`, `Grid`/`GridContainer`, `Title`, `Logo`, `SummaryBox` (the kit has a page but no component set), and `Range slider` (a kit page exists; no Trussworks export found).

Most are layout or wrappers with little to draw. `ErrorMessage` and `ValidationChecklist` matter for form error screens and should be drawn when the first form is wireframed.

## 4. Gaps and decisions this raises

1. **State staff must see pending applications and record a decision.** This is **rule-required**:
   - Rule 3, 3.4(b): the state of qualifying license must "evaluate the PA's eligibility", review the background check, and "issue notice, through the data system", verifying or denying.
   - Rule 3, 3.4(d): the remote state "shall issue a compact privilege".

   **The form it takes is open, not decided:**
   - A sortable, filterable queue would be a *Focus preference*.
   - The two-state pilot with test data may need only a simple list.
   - "Through the data system" may mean states connect from their own licensing systems, with no screen at all.

   Settle how states will connect first (open question). Corrected 2026-10-01: an earlier draft assumed a "staff work queue" without a source.
2. **Custom `Card`:** keep it or switch to the USWDS card? Record the answer as a design decision record (`/author-design-adr`).
3. **Federal banner and identifier:** does a non-federal Commission show them? This is already a candidate design decision from the Q9 brand question.
4. **No step indicator in `FormStep`:** a multi-step application usually shows progress. Is that a Focus preference to add? Not rule-required.
