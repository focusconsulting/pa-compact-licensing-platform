# Wireframe kit

The page templates every screen starts from, and one exemplar screen per portal. Each template is drawn in the [PA Compact Parts Library](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library) on the "Demo: happy path" page; the frame IDs below open it there. [`claude-design-prompt.md`](claude-design-prompt.md) turns a wireframe into a screen.

Every frame is the same three parts: Header, the content in the grid's main column, and Footer and identifier. There is no federal government banner. Regions are listed in page order; anything in `{braces}` is a placeholder.

## Templates

### Wizard step

A form split into a few steps, each a page of related sections. B2 · Apply to join the PA Compact ([`3504:33405`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3504-33405)) is step 1 of 2; B6 · Statements and submit ([`3504:33893`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3504-33893)) is step 2.

1. Step indicator, with the step's name
2. `h1`, and the intro line where the wireframe has one
3. Required fields note
4. Sections, each an `h2` and its fields: Label with Text input, Select, Radio, Checkbox, or Memorable date. A section can end in its own Button, such as "Find my license".
5. Actions: the primary Button, then a Back link

The last step holds what the PA agrees to: each statement with its Checkbox, then the typed-name field and the submit Button.

### Queue

The records waiting on someone. C3 · Applications to review ([`3538:36550`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3538-36550)).

1. `h1`, and the intro line
2. One section per group of records: `h2`, then a Table whose first column links to the case
3. For bulk actions (C3b): a select Checkbox per row, a confirm Checkbox, and the Button

The backlog's QueueList adds a filter chip and an age column; neither is drawn yet.

### Case view

One record, read top to bottom, ending in the reviewer's decision. C4 · Jordan Sample ([`3539:36719`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3539-36719)).

1. Breadcrumb back to the queue
2. `h1`: the person's name, and the date received
3. Sections, each an `h2` with a Table of label and value rows: license details, eligibility, personal information, statements
4. The review section: `h2`, required fields note, the checks as Checkboxes, the decision as Radios, the Button, and a link for the alternative action

### Dashboard

Where each user starts.

- PA, before applying: `h1`, an `h2` with the steps as a Process list, the list of what to have ready, and the Button to start (B1 · Dashboard, [`3504:33283`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3504-33283)).
- PA, once eligible: `h1`, then one `h2` section per record. The qualifying license is a summary line, who verified it, and its StatusTag. Privileges show an empty state and the Button to apply until there are some (C8 · Dashboard: eligible, [`3539:37625`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3539-37625)).
- Staff: `h1` (the state's name), then a Collection with one item per task: its link with a count where it has one, and one line saying what it's for (C2 · Sample State home, [`3538:36309`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3538-36309)).

### Confirm and result

An action that can't be undone opens a Modal over the page it came from (C5 · Confirm decision, [`3539:37050`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3539-37050)). The page after it starts with a success Alert, then either what happens next as a Process list (B9 · Application received, [`3504:34259`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3504-34259)) or the list the user returns to (C6 · Decision recorded, [`3539:37448`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3539-37448)).

### Settings form

Not drawn yet; this is a placeholder until the Commission's settings screens are.

1. `h1`
2. One fieldset per group of settings, each with an `h2`
3. Required fields note, fields, then the Save Button
4. After saving, a success Alert at the top of the same page

## Exemplars

One screen per portal shows a finished template. Each is a DRAFT until the Commission's Product Manager approves it.

| Portal | Exemplar | Template | Approved |
|---|---|---|---|
| PA | C8 · Dashboard: eligible ([`3539:37625`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3539-37625)) | Dashboard | No |
| State | C4 · Jordan Sample ([`3539:36719`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3539-36719)) | Case view | No |
| Commission | Placeholder: none drawn. The draft "Flow: Commission dashboards, reports and payments" page ([`3752:4665`](https://www.figma.com/design/k1W9PxXhtQ3fopcKUePpH9/PA-Compact-Parts-Library?node-id=3752-4665)) will hold it. | Queue | No |
