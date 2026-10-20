# Adapting installed ReUI code (reuse-first, no AI slop)

ReUI items ship production-quality. Your job is to **adapt by reuse** - wire real data and fit the app - not to redesign or hand-roll. The output should look like ReUI built it for this product.

## Preserve the design - don't over-customize

The design IS the product. A ReUI block/component encodes senior-designer decisions: spacing, hierarchy, density, color treatment, and component choices. The fastest way to turn a premium block back into generic AI slop is to "improve" its look - so don't.

- Change **data, copy, and props**; keep the **structure and styling** it ships with. Make the **smallest** change that wires the real data. If your diff touches `className` / JSX structure more than data / props, you are over-customizing - stop and reuse.
- Don't swap ReUI components for hand-rolled ones, restructure the layout, re-skin spacing / radius / colors, or add decorative chrome. Let the installed components carry the default spacing, radius, sizing, icon rhythm, density, and state styling; add custom Tailwind only when a component genuinely lacks a contract you need.
- Want a different look? `search` for a block whose design already fits and reuse that - don't restyle this one into a new design.

## Reuse the parts: examples and the block's own elements

- **Examples are building parts.** A free `c-*` example is a correct, single-pattern composition you can reuse. Before composing from scratch, `get_examples(component)`, install the closest one, and reuse its wiring - assemble UI from examples instead of hand-rolling what an example already shows.
- **Reuse a block's own elements.** Need more rows, cards, items, or sections than ship by default? Repeat the block's **existing** element by mapping real data through the same markup - never invent parallel markup that drifts from its design. Need a variant (empty / loading / expanded)? Derive it from an element the block already has.

## Don't invent (read, don't guess)

- Never write a prop, variant value, import path, or `@reui/...` name you didn't read in a component's inline `api`, an installed example, or a `search` result. If you didn't see it, treat it as nonexistent - call `get_component` / `get_examples` / `search` first, or run the MCP `validate_usage` tool to check planned names + props against the docs before writing code.
- If a getter returns `found: false` or `search` returns nothing, say so and fall back (plain shadcn, or ask) - never fabricate an install command or an API.

## What to change vs leave alone

- **Change:** the item's own data, copy, props, and layout to fit the app.
- **Leave alone:** installed component files, hooks, and the shared theme - do not edit vendored ReUI internals; change behavior through props and the documented API.
- Blocks are **portable React** - no `next/link`, `next/image`, or other framework-runtime imports inside them. Keep them portable.

## Demo data -> real data

- Replace every placeholder with the user's real data. Model it as **typed data structures** and **map over arrays** - never duplicate JSX per row/card. Keep small block-specific formatters next to the data.
- Wire the real source (columns, fields, fetch). For `data-grid`, implement the server fetch contract if the user needs server-side data.
- **Type from the component API, derive during render.** Type domain state through the component's own types - e.g. map status to `BadgeProps["variant"]` via a typed `Record<Status, …>` - instead of stringly-typed values. Compute view state during render; don't mirror derived data into `useState`/`useEffect`.
- **Adapt on the right base.** Use the API for the project's base (Base UI vs Radix - see [components.md](./components.md)); the installed files are already base-correct, so reuse their shape rather than translating from memory.

## Believable content (no AI tells)

- Use realistic labels, counts, timestamps, and statuses that map to a real workflow.
- No decorative buttons, fake tabs, meaningless toggles, equal-weight card walls, empty gradients, ornamental icons, or generic SaaS filler. Every element should do something.

## Operational surfaces (settings / profile / admin)

Pick ONE archetype and keep the family consistent: a vertical rail (3-6 sections), horizontal tabs (5-8), or a frame/stack. Prefer `frame` for tool-like surfaces, a card for profile-like ones. Don't mix archetypes in one surface.
# CLI: registry setup, license, non-interactive install

## Registry setup (one-time, per project)

Free items (the 22 components and all `c-*` examples) need only the plain string registry in `components.json`:

```json
{ "registries": { "@reui": "https://reui.io/r/{style}/{name}.json" } }
```

Premium items (blocks; Motion Icons and templates) require a ReUI license at install:

1. Add the key to `.env.local`:

```bash
REUI_LICENSE_KEY=your-license-key
```

2. Switch `components.json` to the authenticated object form:

```json
{
  "registries": {
    "@reui": {
      "url": "https://reui.io/r/{style}/{name}.json",
      "headers": { "Authorization": "Bearer ${REUI_LICENSE_KEY}" }
    }
  }
}
```

The shadcn CLI expands `${REUI_LICENSE_KEY}` from `.env.local` inside `components.json`. MCP client configs expand environment variables too, but each client has its OWN syntax, so wire the ReUI MCP server with the form that client understands:

- Claude Code (`.mcp.json`, `~/.claude.json`): `"Authorization": "Bearer ${REUI_LICENSE_KEY}"`
- Cursor (`.cursor/mcp.json`) and VS Code: `"Authorization": "Bearer ${env:REUI_LICENSE_KEY}"`
- OpenCode (`opencode.json`): `"Authorization": "Bearer {env:REUI_LICENSE_KEY}"`
- Codex (`~/.codex/config.toml`): `bearer_token_env_var = "REUI_LICENSE_KEY"` - Codex reads the variable itself, so there is no header to write

Only a client with no interpolation at all needs the raw `reui_pat_...` token, and then only in a file that is never committed. Copying the `components.json` form into a client that does not expand it is the common failure: the literal `${REUI_LICENSE_KEY}` placeholder is sent to the server as the credential and every call comes back 401.

The MCP `get_project_context` tool returns the right config. Full guide: https://reui.io/docs/registry?ref=skill

## Installing

Use the project's package runner (check `packageManager`):

```bash
npx shadcn@latest add @reui/<name> --yes      # npm
pnpm dlx shadcn@latest add @reui/<name> --yes  # pnpm
bunx --bun shadcn@latest add @reui/<name> --yes # bun
```

`--yes` skips confirmation prompts. The CLI auto-detects the package manager from the lockfile (there is no `--package-manager` flag). It also resolves the correct base+style variant from `components.json`, so do not pass a style.

## Handling prompts and conflicts

- **Always pass `--yes`** so the CLI does not block on confirmation prompts.
- **Do NOT pass `--overwrite` by default.** If the CLI reports an existing file, read the output and resolve deliberately: install under a different name, adjust the path, or ask the user. Only use `--overwrite` when the user explicitly wants to replace a file.
- **Preview first when touching an existing project**: `npx shadcn@latest add @reui/<name> --dry-run` shows what would change; `--diff <file>` shows a specific file's diff. Use these before overwriting.
- Run from the **project root** so `components.json` and `.env.local` are found.

## Free vs premium boundary

- Public, no key: `c-*` examples and the 22 components (`@reui/data-grid`, `@reui/badge`, ...) that those examples depend on.
- Key required at install: blocks (`@reui/<category>-N`) need a Pro or Ultimate license; Motion Icons (`@reui/icons/...`) and templates need Ultimate.

If an install 401/403s, the license key is missing, invalid, or the plan does not cover that resource (blocks: Pro or higher; icons and templates: Ultimate). Point the user to https://reui.io/account?ref=skill (their key) or https://reui.io/pricing?ref=skill (upgrade).
# ReUI components

The 22 ReUI building blocks: `alert`, `autocomplete`, `badge`, `cascader`, `code-block`, `data-grid`, `date-selector`, `event-calendar`, `filters`, `frame`, `gantt`, `icon-stack`, `icon-tile`, `kanban`, `number-field`, `phone-input`, `rating`, `scrollspy`, `sortable`, `stepper`, `timeline`, `tree`. Examples and blocks are composed from these.

**Rule one: never guess a component's API. Read it first.** Call **`get_component(name)`** for its inline `api` (props + usage, no web fetch), and **share the result's `docsUrl`** (the component's API documentation page) with the user whenever you work with that component's API, so they have the full reference (the `/llms.txt` index is a further fallback). Then call **`get_examples(name)`** to install a worked example and copy real composition. The contracts below are first-try orientation (required props, composition shape, the one gotcha); the inline `api` is the deeper reference. Do not assume you received all of it: a very large API (`cascader`, `filters`, `data-grid`) is trimmed on heading boundaries to fit your context, and every dropped heading is named in `sectionsOmitted`, so a trimmed capsule is a partial read - follow the response's own `next` hint to pull back the part you need instead of guessing at it. `validate_usage` always checks the FULL API, trimmed capsule or not. No single block fits? Compose: search the components you need, read each `get_component`, install a `get_examples` example per component, and adapt.

## data-grid (the flagship - read its API every time)

`data-grid` wraps TanStack Table v9. It is NOT a styled `<table>` and does NOT take `data`/`columns` props directly. The contract:

- Build a TanStack table instance with `useTable({ features: dataGridFeatures, ... })` (columns, data). `dataGridFeatures` is exported by the primitive and already bundles sorting, filtering, pagination, row selection, expanding, pinning, resizing and faceting, so there are no per-table row models to wire.
- Pass that instance to `<DataGrid table={table} recordCount={total}>`.
- Compose the body with `DataGridTable` inside `DataGrid`, and enable features through `tableLayout` (e.g. `{ headerSticky: true, columnsResizable: true }`), not ad-hoc classes.
- Server-side data uses the documented fetch shape (`recordCount` is the total for pagination).

```tsx
const table = useTable({
  features: dataGridFeatures,
  data,
  columns,
})

<DataGrid table={table} recordCount={data.length}>
  <DataGridTable />
</DataGrid>
```

Common mistakes:

- **Incorrect:** `<DataGrid data={rows} columns={cols} />` - these props do not exist. **Correct:** build a `useTable({ features: dataGridFeatures, ... })` instance and pass `table={table}` + `recordCount`.
- **Incorrect:** a raw `<table>` / hand-rolled pagination. **Correct:** use `data-grid`; read its API for sticky header, pagination, virtualization, row selection.
- **Incorrect:** styling rows/cells with arbitrary classes. **Correct:** drive layout via `tableLayout` and the primitive's `DataGridColumnMeta` (e.g. `cellClassName`, `headerTitle`), set through the bundle's `columnMeta` slot.

## event-calendar

**Required:** events via `events`/`onEventsChange` (controlled) or `defaultEvents` (uncontrolled), plus a height on the root.
**Shape:**

```tsx
<EventCalendar defaultEvents={events} defaultView="month" className="h-[560px]">
  <EventCalendarNav />
  <EventCalendarContent />
</EventCalendar>
```

**Gotcha:** headless-first: `EventCalendarContent` renders the active view (month/week/day/days/agenda; a resource view activates when `resources` is passed) - there is no per-view JSX to compose. Events are `{ id, title, start, end (exclusive), allDay?, color?, recurrence?, resourceId? }`. Mutations flow through `onEventUpdate`/`canDropEvent` (return `false` to reject); the root needs an explicit height because it is a min-h-0 flex column.

## gantt

**Required:** `resources` (the left tree) plus bars via `events`/`defaultEvents` attached by `resourceId`.
**Shape:**

```tsx
<Gantt defaultEvents={bars} resources={tasks} defaultScale="month" className="h-[480px]">
  <GanttNav />
  <GanttView />
</Gantt>
```

**Gotcha:** bars move along the time axis only (never across rows) and are all-day spans with exclusive `end`; `progress` is 0-100. Scales are `day | week | month | quarter | year`. Zoom control, infinite scroll, summary rollups, and row checkboxes are ON by default - turn off what you do not need. Same `onEventUpdate`/`canDropEvent` commit pipeline as `event-calendar`; the root needs an explicit height.

## kanban

**Required:** `value` (`Record<string, T[]>`), `onValueChange`, `getItemValue`
**Shape:**

```tsx
<Kanban value={cols} onValueChange={setCols} getItemValue={(i) => i.id}>
  <KanbanBoard>
    {Object.entries(cols).map(([id, items]) => (
      <KanbanColumn key={id} value={id}>
        <KanbanColumnHandle><h3>{id}</h3></KanbanColumnHandle>
        <KanbanColumnContent value={id}>
          {items.map((i) => (
            <KanbanItem key={i.id} value={i.id}>
              <KanbanItemHandle>{i.title}</KanbanItemHandle>
            </KanbanItem>
          ))}
        </KanbanColumnContent>
      </KanbanColumn>
    ))}
  </KanbanBoard>
  <KanbanOverlay><div className="bg-muted size-full rounded-md" /></KanbanOverlay>
</Kanban>
```

**Gotcha:** state is `Record<columnId, T[]>`. Each `KanbanColumnContent value` must match its parent `KanbanColumn value`. Omit `KanbanOverlay` and the drag preview silently breaks.

## sortable

**Required:** `value` (`T[]`), `onValueChange`, `getItemValue`
**Shape:**

```tsx
<Sortable value={items} onValueChange={setItems} getItemValue={(i) => i.id}>
  {items.map((i) => (
    <SortableItem key={i.id} value={i.id}>
      <SortableItemHandle><GripVertical /></SortableItemHandle>
      {i.label}
    </SortableItem>
  ))}
</Sortable>
```

**Gotcha:** a flat 1D reorder list (not columns - that is `kanban`). `getItemValue` must return a stable, unique string. Pass `layout="grid"` or `layout="nested"` for non-list layouts.

## filters

**Required:** `fields` (`FilterField[]`). The value is ONE `FilterQuery` tree - `query` + `onQueryChange`, or uncontrolled `defaultQuery`.
**Shape:**

```tsx
const fields: FilterField[] = [
  { id: "title", label: "Title", type: "text" },
  {
    id: "status",
    label: "Status",
    type: "select",
    options: [
      { value: "active", label: "Active" },
      { value: "archived", label: "Archived" },
    ],
  },
]
const [query, setQuery] = useState<FilterQuery>(() => createFilterQuery())

<Filters fields={fields} query={query} onQueryChange={setQuery} />
```

**Gotcha:** the state is a TREE, not a list of chips. `FilterQuery` is a group of rules joined by `and`/`or` and a group may hold another group, so `(A and B) or C` is expressible; a rule is `{ id, type: "rule", path: ["status"], operator, value }` and `path` is the whole nested attribute path, root first. The pre-rewrite API is GONE: there is no `filters`/`onChange` prop, no `FilterFieldConfig` (fields are `FilterField`, nested through their own `fields`, keyed `id` not `key`), and no `createFilter()` - it minted ids inside a pure function and broke hydration, so ids now come from `createFilterIdFactory(seed)` seeded off `useId`, and `createFilterQuery()` / `createFilterRule()` take one. Read the query back with `flattenFilterConditions` (`{ path, field, operator, values, negated }` per rule, incomplete rules skipped) and walk the tree yourself when the parentheses carry meaning - the primitive compiles nothing, no SQL, no query string.

`variant` picks the chrome over that one query: `"basic"`, the default, is the flat chip row for a toolbar over a table; `"advanced"` is the condition builder, hung off a trigger or rendered in place with `advancedMode="inline"`. Both read and write the same tree, so a saved view built in one opens in the other. Other props worth knowing before you hand-roll them: `size` is two rungs, `"sm" | "default"`, resolved per style (there is no `lg`); `reorderable` turns on drag and Alt+Arrow row moves in the builder; `onBeforeQueryChange` is the ONE veto point for every write (return `false` to refuse, it cannot rewrite); `editors` registers custom value editors a field selects by `editor` name; `labels` / `operatorLabels` own every rendered string; `pathCollapse` + `maxPathSegments` shorten deep attribute paths; `renderChip` / `renderValue` / `renderEmpty` replace rendered parts. On a field, `loadOptions` supplies async options with paging and `resolveValues` renders a chip restored from a saved view whose option was never loaded. Pairs naturally with `data-grid`.

## cascader

**Required:** `items` (a tree of `{ value, label, children? }`), plus the panel parts inside `CascaderContent`.
**Shape:**

```tsx
<Cascader items={items} value={value} onValueChange={setValue}>
  <CascaderTrigger render={<Button variant="outline" />}>
    <CascaderValue placeholder="Select an attribute" />
  </CascaderTrigger>
  <CascaderContent className="w-80">
    <CascaderPanel>
      <CascaderNav>
        <CascaderBreadcrumb />
        <CascaderInput />
      </CascaderNav>
      <CascaderEmpty />
      <CascaderList maxHeight={288}>
        <CascaderItems />
      </CascaderList>
      <CascaderStatus />
    </CascaderPanel>
  </CascaderContent>
</Cascader>
```

**Gotcha:** pressing a branch NAVIGATES, it does not select - only leaves are selectable until you pass `selectable="any"` or a predicate, and once a branch is selectable its chevron becomes the only way to open it. `CascaderInput` must stay inside `CascaderContent` (Base UI refills the query from the selection when the input sits outside the popup). Always include `CascaderStatus`: it is the live region announcing level changes, which the visual breadcrumb does not provide to screen readers. Accepts a flat adjacency list via `getParent` as well as nested `children`. `searchScope="deep"` searches every level and annotates results with their path; `multiple` gives checkbox rows; `inline` + a bare `CascaderPanel` embeds it with no popover.

The shape above is `mode="drill"`, the default. `mode="tree"` keeps the same parts (drop `CascaderBreadcrumb`, pass `showBack={false}`, drive expansion with `expanded`/`onExpandedChange`); `mode="columns"` REPLACES `CascaderList` + `CascaderItems` with a single `CascaderColumns`, and has no breadcrumb. Other props worth knowing before you hand-roll them: `cascade` (multi-select only, parent/child selection with indeterminate branches - pair it with `selectable="any"`, since a leaf-only tree can never cascade), `indicator={false}` to drop the single-select check and its gutter (visual only, no-op with `multiple`), `virtualize`/`virtualizeThreshold` plus `CascaderVirtualItems` for long levels, and `getChildren` for async levels with cursor paging, retry on failure and optional `prefetch`. `CascaderFooter` pins commands below the list (`actions` is the quick path) and `CascaderSubmenu` opens one as a side-anchored flyout with the full menu keyboard model. To head a run of rows use `CascaderGroup` wrapping a `CascaderLabel` - a bare label inside a listbox names nothing and is dropped from the accessibility tree - and `CascaderSeparator` for the rule between runs. Every rendered string comes from `labels`, and the panel is RTL-correct under a `DirectionProvider` or `dir="rtl"`.

## date-selector

**Required:** none, but wire `onChange` to capture the value.
**Shape:**

```tsx
const [value, setValue] = useState<DateSelectorValue | undefined>()

<DateSelector value={value} onChange={setValue} label="Due date" />
```

**Gotcha:** the value is a structured `DateSelectorValue` (period / operator / start+end dates), NOT a `Date` - never pass a raw `Date`. Use `allowRange={false}` to lock single-date picking. Read `get_component("date-selector")` for the value shape.

## tree

**Required:** `tree` (a `@headless-tree/core` instance you construct)
**Shape:**

```tsx
<Tree tree={tree}>
  {tree.getItems().map((item) => (
    <TreeItem key={item.getId()} item={item}>
      <TreeItemLabel />
    </TreeItem>
  ))}
</Tree>
```

**Gotcha:** `Tree` is a styled shell - it takes a headless-tree instance via `tree`, NOT `data`/`items` props. Build the instance with `@headless-tree/react`. External API: https://headless-tree.lukasbach.com/

## stepper

**Required:** `StepperItem step` (number), `StepperContent value` (number)
**Shape:**

```tsx
<Stepper defaultValue={1}>
  <StepperNav>
    <StepperItem step={1}>
      <StepperTrigger><StepperIndicator>1</StepperIndicator></StepperTrigger>
      <StepperSeparator />
    </StepperItem>
    <StepperItem step={2}>
      <StepperTrigger><StepperIndicator>2</StepperIndicator></StepperTrigger>
    </StepperItem>
  </StepperNav>
  <StepperPanel>
    <StepperContent value={1}>Step 1 content</StepperContent>
    <StepperContent value={2}>Step 2 content</StepperContent>
  </StepperPanel>
</Stepper>
```

**Gotcha:** steps are 1-indexed. Without `StepperPanel` + `StepperContent` you render the nav trail but no body. Put `StepperSeparator` in every `StepperItem` except the last.

## timeline

**Required:** `TimelineItem step` (number)
**Shape:**

```tsx
<Timeline>
  <TimelineItem step={1}>
    <TimelineHeader>
      <TimelineDate>March 2024</TimelineDate>
      <TimelineTitle>Project initialized</TimelineTitle>
    </TimelineHeader>
    <TimelineIndicator />
    <TimelineSeparator />
    <TimelineContent>Repo and architecture set up.</TimelineContent>
  </TimelineItem>
</Timeline>
```

**Gotcha:** each item needs a unique `step`. `orientation` is `"vertical"` (default) or `"horizontal"`. This is a static event display, not interactive like `stepper`.

## autocomplete

**Required:** `items` (array; each item has at least `value`)
**Shape:**

```tsx
<Autocomplete items={items}>
  <AutocompleteInput placeholder="Search..." />
  <AutocompleteContent>
    <AutocompleteEmpty>No results found.</AutocompleteEmpty>
    <AutocompleteList>
      {(item) => (
        <AutocompleteItem key={item.value} value={item}>{item.label}</AutocompleteItem>
      )}
    </AutocompleteList>
  </AutocompleteContent>
</Autocomplete>
```

**Gotcha:** `AutocompleteList` takes a render-prop `(item) => ReactNode`, NOT a mapped array of children. External API: https://base-ui.com/react/components/autocomplete

## phone-input

**Required:** none, but wire `onChange`.
**Shape:**

```tsx
<PhoneInput placeholder="Enter phone number" defaultCountry="US" value={value} onChange={setValue} />
```

**Gotcha:** `value`/`onChange` use an E.164 string (e.g. `"+14155551234"`), not a display-formatted string; `onChange` can fire `undefined`. `defaultCountry` is a 2-letter ISO code. Wraps `react-phone-number-input`.

## number-field

**Required:** wrap the controls in `NumberFieldGroup`.
**Shape:**

```tsx
<NumberField defaultValue={0}>
  <NumberFieldScrubArea label="Quantity" />
  <NumberFieldGroup>
    <NumberFieldDecrement />
    <NumberFieldInput />
    <NumberFieldIncrement />
  </NumberFieldGroup>
</NumberField>
```

**Gotcha:** import from `@/components/ui/number-field`. The accessible label goes on `NumberFieldScrubArea`, not `NumberField`. External API: https://base-ui.com/react/components/number-field

## rating

**Required:** `rating` (number)
**Shape:**

```tsx
<Rating rating={4.5} showValue editable onRatingChange={setRating} />
```

**Gotcha:** supports decimals (partial stars). Pass `editable` + `onRatingChange` for interactive input; omit both for a read-only display.

## scrollspy

**Required:** `targetRef` (the scroll container ref)
**Shape:**

```tsx
<Scrollspy targetRef={containerRef}>
  <a href="#s1" data-scrollspy-anchor="s1">Section 1</a>
  <a href="#s2" data-scrollspy-anchor="s2">Section 2</a>
</Scrollspy>
<div ref={containerRef}>
  <div id="s1">...</div>
  <div id="s2">...</div>
</div>
```

**Gotcha:** each link's `data-scrollspy-anchor` must match a section `id`. `targetRef` is the scrollable container (defaults to the window).

## frame

**Required:** `Frame` > `FramePanel`
**Shape:**

```tsx
<Frame>
  <FramePanel>
    <FrameHeader>
      <FrameTitle>Title</FrameTitle>
      <FrameDescription>Description</FrameDescription>
    </FrameHeader>
    <div className="p-5">Content</div>
    <FrameFooter>Footer</FrameFooter>
  </FramePanel>
</Frame>
```

**Gotcha:** a structured card shell for tool-like surfaces. `stacked` connects multiple panels with shared borders; `dense` removes panel padding; radius via the `--frame-radius` CSS variable.

## icon-stack

**Required:** one child icon
**Shape:**

```tsx
<IconStack aria-hidden="true">
  <InboxIcon className="size-4" />
</IconStack>
```

**Gotcha:** isometric layered artwork for empty states and illustrations; style the inner icon via its own `className`. Mark purely decorative stacks `aria-hidden="true"` and keep the real label in surrounding copy.

## icon-tile

**Required:** one child icon
**Shape:**

```tsx
<IconTile variant="elevated" size="lg">
  <PackageIcon />
</IconTile>
```

**Gotcha:** the square container an icon sits in, so every list row, feature card and empty state shares one affordance. `variant`: `outline` (default) | `elevated` (muted fill, raised ring) | `soft` (tinted nested, tone from currentColor) | `solid` (filled tone, contrasting glyph) | `frame` (double container). `soft` and `solid` retint from one text color class (they default to `text-primary`). `size`: `xs | sm | default | lg | xl` (24/32/40/48/64px tile, glyph scales 12/14/16/20/24px). `radius`: `default | full`. Do not set a `size-*` class on the child icon unless you mean to override the tile's glyph size; recolor with `className` on the tile, not the icon.

## code-block

**Required:** `code` + `language`, or pre-highlighted `lines`.
**Shape:**

```tsx
<CodeBlock code={code} language="tsx" />

<CodeBlock code={code} language="tsx" showLineNumbers maxLines={20}>
  <CodeBlockHeader>
    <CodeBlockTitle>use-totals.ts</CodeBlockTitle>
    <CodeBlockLanguage />
    <CodeBlockCopyButton className="ml-auto" />
  </CodeBlockHeader>
  <CodeBlockExpandButton />
</CodeBlock>
```

**Gotcha:** the one-liner is already a complete block; every child (header, title, language label, copy button, wrap toggle, expand button, line actions) is optional chrome, at any depth. Shiki is the only npm dependency and loads lazily, one chunk per language, on first highlight; `lines` (from `highlightCode` in `code-block-highlight`, which is server-safe and has no `"use client"`) or `highlight={false}` loads nothing at all. `maxLines` caps the height AND marks the block collapsible, which is what makes `CodeBlockExpandButton` appear. Use `variant="ghost"` when the block sits inside a surface that already has a border.

## alert

**Required:** `Alert` > `AlertTitle`
**Shape:**

```tsx
<Alert variant="success">
  <ShieldCheckIcon />
  <AlertTitle>Security update</AlertTitle>
  <AlertDescription>Enable two-factor authentication.</AlertDescription>
  <AlertAction><Button size="xs">Update</Button></AlertAction>
</Alert>
```

**Gotcha:** shadcn-compatible API. `variant`: `default | destructive | info | success | warning | invert`. The non-default variants use ReUI extended color tokens (`--success`/`--info`/`--warning`/`--invert`), which the install adds. Defer generic alert rules to the shadcn skill.

## badge

**Required:** none (text child).
**Shape:**

```tsx
<Badge variant="success-light" size="sm">Success</Badge>
<Badge variant="outline" radius="full">Pill</Badge>
```

**Gotcha:** shadcn-compatible. Rich `variant` set (solid, `-outline`, `-light` per color), `size` `xs..xl`, `radius` `default | full`. Like `alert`, the color variants rely on ReUI extended tokens. Prefer `Badge` variants over raw color classes for statuses.

## base vs radix - write for the project's base

ReUI ships every component in two builds: `base` (Base UI) and `radix` (Radix UI). The install command and name are identical, and the CLI installs the build matching the project. But you must write/adapt code against the **right base**, because their APIs differ.

**Detect the base first.** Read `components.json` -> `style` and take the segment before the first `-`:

- `"style": "base-nova"` -> **Base UI**
- `"style": "radix-nova"` -> **Radix UI**

**Then use that base's API.** The deltas mirror shadcn's base-vs-radix split:

- Slot/composition: Base UI `render={<… />}` vs Radix `asChild`.
- `Select`: Base UI takes `items`; Radix uses `<SelectItem>` children.
- `ToggleGroup`: Base UI `multiple` boolean vs Radix `type="single" | "multiple"`.

The safest path is to **read the installed files and `c-*` examples** - they're already in your base, so reuse their wiring instead of guessing. When `get_component`'s inline `api` or an example shows the other base's shape, translate it to your base (or `validate_usage` to confirm). Defer the generic base/radix mechanics to the shadcn skill.
# Craft: make ReUI UI exceptional, not generic

ReUI items ship senior-designer quality. Your adaptation has to hold that bar, so the result reads like a real product surface a team would keep - not a wireframe an AI generated. Use these alongside the reuse rules in [adapting.md](./adapting.md).

## Have a point of view

Pick an emotional register before you compose - calm, operational, premium, editorial, dense, energetic - and let layout, spacing, surface treatment, and icon behavior all reinforce it. One or two memorable decisions and restraint everywhere else beats ten generic ones. UI with no point of view reads as generated.

## Brutally clear hierarchy

One focal point per card or panel: the dominant metric or task first, its label second, supporting detail third. The first thing the eye lands on should be the right thing; secondary text must read as secondary. Borders, separators, and surfaces do real work to create 2-3 information bands - don't flatten everything to equal weight.

## Spacing rhythm and deliberate density

Gaps are a signal, not a default. Keep them intentional and consistent within a family (`gap-1`/`gap-2` for tight operational rows, larger gaps for section breaks), and smaller within a group than between groups. Match the surrounding ReUI density; don't pad an operational surface like a marketing page, and don't drift density mid-section. The composition should still feel authored in grayscale.

## Cover the real states (the usual miss)

A surface isn't done at the happy path. Compose, and wire:

- **Empty** - a purposeful empty state (short message + the primary action), never a blank panel.
- **Loading** - a **skeleton** that matches the real layout, not a centered spinner.
- **Error** - an inline, recoverable error with a retry, announced via `role="status"`/`aria-live`.

Derive these from an element the block already has (don't invent parallel markup), or `get_examples` for a state-specific example.

## Responsive by default

Mobile-first, not mobile-afterthought. In constrained rows/cards/sidebars, put `min-w-0` on the shrinking container and `truncate` long single-line labels; protect the primary label's width and let secondary content compress. Reflow layouts (multi-column -> single column) rather than just shrinking them. Desktop and mobile should both look designed.

## Motion, subtly

Motion should clarify, not decorate. Use ReUI Motion Icons on primary actions for a subtle hover cue; keep transitions short (~200-300ms) with calm easing; prefer a skeleton pulse over a spinner. No bouncing, no gratuitous entrance animations on every element.

## Real, activated content

Use believable, typed data (realistic labels, counts, timestamps, statuses that map to a real workflow) - never lorem or abstract filler. Every visible control does something: no decorative buttons, fake tabs, meaningless toggles, or stats with no job. It must still hold with long names, empty values, and crowded data.

## Avoid the AI tells

These instantly read as generated - don't ship them: equal-weight card walls, empty gradients, repetitive padding everywhere, generic enterprise copy, ornamental icons, and number tiles that don't earn their place.

## The bar

Before you finish, ask: **would a product team keep this instead of replacing it? Does it still feel strong after swapping in real content?** If not, reuse the shipped ReUI design harder - don't restyle it into something new - then run the [quality.md](./quality.md) gates.
# Icons (ReUI delta over shadcn)

Follow the shadcn icon rules (use the project's configured `iconLibrary`, `data-icon` on icons inside `Button`, no sizing classes on icons inside components, pass icons as component objects not string keys). ReUI adds the following.

## Portable icons (library-agnostic)

ReUI components, examples, and blocks are authored to be icon-library-agnostic. When `iconLibrary` is set in `components.json`, the shadcn CLI installs each item's icons in **your** library automatically - you swap nothing. If an installed item's icons don't match your project (for example `iconLibrary` isn't set, so they came in from the item's demo library), change the **import source and component name** to your library, keeping the same icon-name semantics:

- `lucide` -> `lucide-react`
- `tabler` -> `@tabler/icons-react`
- `phosphor` -> `@phosphor-icons/react`
- `remix` -> `@remixicon/react`
- `hugeicons` -> `@hugeicons/react`

Don't assume `lucide-react`; read `iconLibrary` from `components.json`.

## Keep icons purposeful

Icons support the hierarchy, they don't replace it: keep them small, matched to the surrounding density, and decorative ones `aria-hidden="true"` (an icon-only control still needs an accessible label on the control). Don't add ornamental icons that do no job.

## Motion Icons (the `@reui/icons/...` set)

ReUI ships its own icon set in 4 styles (outline, solid, duotone, filled), each icon in two variants:

```bash
npx shadcn@latest add @reui/icons/default/<style>/<name> --yes    # static
npx shadcn@latest add @reui/icons/animated/<style>/<name> --yes   # hover-animated (motion/react)
```

Motion Icons need an Ultimate license for **both discovery and install** (`REUI_LICENSE_KEY`, see [cli.md](./cli.md)). Without it `search_icons` comes back `locked` with no results and `search` returns no icons at all, so check the plan before you promise the user icons: on a free or Pro account, use the project's own `iconLibrary` instead. Reach for a Motion Icon on a primary action when a subtle hover cue helps; keep motion restrained.

Finding icons:

- Several icons (the common case): **`search_icons(concepts[])`** - up to 24 concepts in one call, the best icons per concept with install commands. Pass `animated: true` to get only icons with a hover-animated Motion variant.
- One icon: `search` with `type: "icon"`.
- Icon results and `get_icon` carry `animated: true` and `installAnimated` when an animated variant exists - use those install strings, do not construct paths by hand.
- Every icon result carries a `previewUrl` (its live icon-category page) - **share it with the user** so they can SEE the icon before installing.

The `icon-stack` component composes multiple icons into a stacked display.
# Quality gates (security, accessibility, scroll)

These are the **done gate**, not a nice-to-have: before you call any ReUI work finished, call the MCP `get_audit_checklist` tool and pass every item below (plus the craft bar in [craft.md](./craft.md)). Then typecheck and lint.

## Security

- Never `dangerouslySetInnerHTML`. Render data as text/components.
- External links (`target="_blank"`) must always pair `rel="noopener noreferrer"`.
- No real PII, secrets, or tokens in demo or committed code. Remote media only from sources the project already allows.

## Accessibility

- Implicit list/card items that navigate get real anchors with a standard hover affordance.
- Icon-only or numeric buttons need an `aria-label`; decorative icons get `aria-hidden`.
- Every non-submit button is `type="button"`.
- Keyboard + focus: everything interactive is reachable in a sensible Tab order with a visible focus ring; layers (dialogs/sheets/menus) trap focus and close on `Escape`. ReUI components ship standard keyboard behavior - read each component's inline `api` rather than re-implementing it.
- Announce async UI: loading and error messages use `role="status"` / `aria-live` so they're not silent to screen readers.

## Scroll mechanics

- Make scroll regions with a parent-owned height: a `min-h-0` + flex chain down to the scroll container. Never guess a `max-h`.
- The scroll container owns `overflow-auto`; ancestors stay `min-h-0` so the height resolves.
# ReUI registry structure

ReUI is a shadcn-compatible registry with four entity types. **Examples and blocks are built FROM components** - reuse them, don't rebuild.

- **component** - one of the 22 ReUI building blocks with a real API (`data-grid`, `kanban`, `filters`, `date-selector`, `tree`, ...). Install directly (`@reui/data-grid`) or let it come in as a dependency of an example/block. Free. Read its API with `get_component(name)`.
- **example** - a free `c-*` single-pattern use-case of a component (`c-kanban-1`, `c-data-grid-3`). Install one and read it to copy real composition. Find a component's examples with `get_examples(name)`.
- **block** - a premium, full-page section that composes several components (`data-grid-base-2`, `settings-2`). Pro or Ultimate license at install. Adapts to your active theme via semantic tokens.
- **icon** - Motion Icons in 4 styles (outline, solid, duotone, filled), static (`@reui/icons/default/<style>/<name>`) and hover-animated (`@reui/icons/animated/<style>/<name>`). Ultimate license at install. See [icons.md](./icons.md).

## The @reui registry

Install everything through the shadcn CLI: `npx shadcn@latest add @reui/<name> --yes`. The CLI reads the `@reui` registry from the project's `components.json`. Free items need only the plain string form:

```json
{ "registries": { "@reui": "https://reui.io/r/{style}/{name}.json" } }
```

Premium installs need the authenticated form + `REUI_LICENSE_KEY` in `.env.local` - see [cli.md](./cli.md). The MCP `get_project_context` tool returns the right config.

## Know your base: base or radix

ReUI ships every item in two builds - `base` (Base UI) and `radix` (Radix UI) - with mirrored names. The CLI installs the build matching your project automatically, but **you must write code against the right base's API**. Detect it from `components.json` -> `style`: the segment before the first `-` is the base (`base-nova` -> Base UI, `radix-nova` -> Radix UI). The installed files and `c-*` examples are already in your base - read them and adapt on that base. See [components.md](./components.md) for the API deltas.

**So the MCP's own `docsUrl` and `previewUrl` match your base**, send your `style` to the MCP: add `?style=<your components.json style>` to the ReUI MCP server URL (or set an `X-Reui-Style` header) in your MCP client config - set once, applies to every call. The MCP then resolves docs/preview links to YOUR library (`/docs/components/radix/...`, `/preview/radix/...` for a radix project) instead of the default base; `get_project_context` echoes back the style it currently sees so you can confirm it. Install commands are unaffected (the CLI already installs the right variant). If you notice the MCP returning `base` links for a `radix` project, tell the user to add `?style=` to the server URL.

Blocks adapt to your active theme through semantic tokens and CSS variables - change the theme and every block follows.

## Free vs premium

- **Free, no license key:** the 22 components, all `c-*` examples, and this skill. The MCP is free too but still needs a free ReUI account (the agent signs in on first use); a license key is only for premium installs.
- **Premium, license required at install:** blocks (Pro or Ultimate), Motion Icons and templates (Ultimate). Set `REUI_LICENSE_KEY` (see [cli.md](./cli.md)).

## Component API index

The canonical index of every component's API docs is **https://reui.io/llms.txt** (returned as `componentsApiUrl` in MCP results). Prefer the inline `api` from `get_component`; use the index/docs as the fallback.
# Styling (ReUI delta over shadcn)

Follow the shadcn skill for the generic rules (semantic colors not raw values, `gap-*` not `space-y-*`, `size-*`, `cn()`, no manual `dark:` overrides, no overlay `z-index`). This file is only the ReUI-specific additions.

## ReUI extended semantic tokens

ReUI adds semantic tokens beyond shadcn's base set. Use these instead of raw colors for status and emphasis:

- `--success` / `--success-foreground`
- `--info` / `--info-foreground`
- `--warning` / `--warning-foreground`
- `--destructive-foreground` (paired with shadcn's `--destructive`)
- `--invert` / `--invert-foreground` (inverted surfaces)

Use them as Tailwind utilities (`bg-success text-success-foreground`, `text-warning`, ...). They are defined in the project's global CSS and registered with Tailwind (`@theme inline` on v4). If a token is missing in the project, add it to the global CSS file (never a new file) following the same `name` / `name-foreground` convention, exactly as the shadcn customization rules describe.

**Incorrect:** `<span className="text-green-600">Active</span>`
**Correct:** `<Badge variant="success">Active</Badge>` or `<span className="text-success">Active</span>`

## Blocks follow your theme

When you install a block it adapts to your active theme through the semantic tokens above and the project's CSS variables. Don't hardcode style-specific values into installed block code and don't fork it to "restyle" - change the theme via the CSS variables / a preset and every block follows. Want a different look? `search` for a block whose design already fits instead of re-skinning one.

## Density and typography rhythm

ReUI operational UI usually feels dense, not airy. Keep the gap between a title and its supporting description tight by default (`gap-0.5`, `space-y-1`, or `space-y-px`), and smaller than the gap between sections. Match the surrounding ReUI density when you add rows or fields; do not pad operational surfaces like a marketing page.
# Workflow: find -> install -> read API -> adapt

The core ReUI loop. The MCP tells you what to install and gives you the API; the shadcn CLI installs it; you turn the installed files into correct, themed, data-wired code by **reuse**, not redesign.

## 1. Find (ReUI MCP `search` / `compose_page`)

**Full multi-section page ask?** Call `compose_page(intent, sections?)` FIRST, before searching block-by-block. It returns ordered sections, each with the best block for the intent (top pick + alternates); on a free account it answers `mode: "free"` and fills the same sections with free `c-*` examples instead, so the plan is always buildable. Sections listed in `unavailableSections` have no real inventory - compose those from components, do not force a bad block.

For everything else, call `search` with the user's intent. Pass structured hints whenever you can infer them - you are an LLM, so do the parsing the server cannot:

- `type`: `"component"` (one of the 22 building blocks), `"example"` (a c-\* use-case), `"block"` (a full page/section), `"icon"`.
- `component`: the ReUI component the request implies (`"data-grid"`, `"kanban"`, ...).
- `category`, `features` (e.g. `["sortable","pagination"]`), `free`.

Example: "build a users management page with filters" -> `search({ query: "users management page with filters", type: "block", component: "data-grid", features: ["filters"] })`.

Each result has `install`, `previewUrl`, `docsUrl`, `componentsUsed`, `score`, `termCoverage`, and `whyMatch`. `score` is relative to the top hit (the top is ~100 by construction), not an absolute quality - compare results to each other, and show the user the top options if several score closely; do not silently guess. A low `termCoverage` means a weak match even with a high score - rephrase or widen.

Results are scoped to the account's plan, so you are never shown an item the user could not install: blocks need Pro, Motion Icons need Ultimate. A `type` hint the plan cannot use (or a query whose only matches are premium) comes back as a normal HTTP 200 answer with `locked: true` and `requiredPlan` rather than results - that is a paywall, not a missing item, so switch to free components and `c-*` examples and mention https://reui.io/pricing?ref=skill.

**Always show the preview link.** Whenever you list or recommend items - from `search`, `search_icons`, `list_components`, `compose_page`, or a getter - include each item's `previewUrl` (a live preview page) so the user can SEE it before you install. Blocks and examples link to an individual live preview; icons and components to their live category/component page. This applies to every listing, not only a single pick. Where a result carries `thumbnail` (blocks and `c-*` examples), show the image itself as markdown linked to `previewUrl`, so the user sees the block before you install it.

## 2. Install (shadcn CLI)

Run the result's `install` command from the project root, non-interactively:

```bash
npx shadcn@latest add @reui/<name> --yes
```

The CLI reads `components.json`, installs the correct base+style variant, resolves `registryDependencies` (a block pulls in its components), installs npm deps, and rewrites aliases. Do not pass the base/style. See [cli.md](./cli.md).

## 3. Read the API (do not guess props)

Before writing code against any component an item uses:

1. The item's `componentDigests` already give a 1-line contract per component - often enough to wire it. For the deeper API, call **`get_component(names)`** with ALL of `componentsUsed` in ONE call (it accepts an array) and read each inline `api` - no web fetch. A very large API is trimmed on heading boundaries to fit your context and lists what it dropped in `sectionsOmitted`; when the part you need is in that list, re-read it as the response's `next` hint says rather than guessing. `validate_usage` always checks the FULL API, so it still catches a prop you invented from a trimmed capsule. **Share the component's `docsUrl`** (its API documentation page) with the user whenever you work with that component's API, so they have the full reference; the `/llms.txt` index is a further fallback.
2. Call **`get_examples(name)`** for the free `c-*` examples of that component; install one and **read the added files** to copy the exact composition. This is the fastest correct path - the example shows real wiring you adapt, not invent.
3. About to write a prop you did not see in an `api` or installed file? Run **`validate_usage`** BEFORE writing the code - per-prop documented / notDocumented verdicts plus did-you-mean suggestions. notDocumented means read the API, not push on.

## 4. Adapt (reuse-first) - do not skip

Installing files is not the end, and redesigning them defeats the point. First note the project's **base** so you write the right API - read `components.json` -> `style` and take the segment before the first `-` (`base-nova` -> Base UI, `radix-nova` -> Radix UI), see [components.md](./components.md). After `add`:

1. **Read the added files**; keep the composition intact. For a block, verify the components are wired correctly (for `data-grid`: a `useTable({ features: dataGridFeatures, ... })` instance passed as `table`, `recordCount` set - see [components.md](./components.md)).
2. **Replace demo data with the user's real data** via typed structures (see [adapting.md](./adapting.md)).
3. **Fix icon imports** to the project's icon library (see [icons.md](./icons.md)).
4. **Align styling** to semantic tokens and the active theme - no raw colors (see [styling.md](./styling.md)).
5. **Validate before finalizing**: if your adaptation introduced components or props you did not read in an `api` or example, run `validate_usage` on them.
6. **Hit the craft bar** - clear hierarchy, deliberate density, the empty / loading / error states, subtle motion, and mobile-first responsiveness (see [craft.md](./craft.md)). Generic-looking output means you under-reused the design, not that it needs restyling.
7. **Pass the quality gates** (security, a11y, scroll) - call the MCP `get_audit_checklist` tool and clear every item (see [quality.md](./quality.md)).
8. **Typecheck / lint**.

## If no single block fits

Compose from components (`compose_page` tells you which sections have no block inventory via `unavailableSections`). `search` the components you need, read each `get_component` API, install a worked `get_examples` example for each, and assemble by adapting those examples. A block in the same category is a useful reference - install it and read its files to see how ReUI composes those components, then adapt.
