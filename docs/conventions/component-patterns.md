---
id: conventions-component-patterns
title: Component Patterns - shadcn/ui with @base-ui/react
domain: conventions
tags: [conventions, shadcn, base-ui, no-asChild, buttonVariants, render-prop, radix, components]
related: [conventions-frontend, frontend-layout]
summary: "shadcn/ui uses @base-ui/react (NOT @radix-ui). No asChild prop. Use buttonVariants() for link styling, render prop for trigger composition."
---

# Component Patterns

## CRITICAL: No asChild

This project's shadcn/ui uses `@base-ui/react`, NOT `@radix-ui/react`. The `asChild` prop **does NOT exist**.

### Link styled as Button

```tsx
// ❌ WRONG - asChild does not exist
<Button asChild><Link href="/path">Click</Link></Button>

// ✅ CORRECT - use buttonVariants
import { buttonVariants } from "@/components/ui/button";
<Link href="/path" className={buttonVariants({ variant: "outline", size: "sm" })}>
  Click
</Link>
```

### DropdownMenu Trigger with Button

```tsx
// ❌ WRONG
<DropdownMenuTrigger asChild><Button>Menu</Button></DropdownMenuTrigger>

// ✅ CORRECT - use render prop
<DropdownMenuTrigger render={<Button variant="ghost" />}>
  Menu
</DropdownMenuTrigger>
```

### Dialog/Sheet Close with Button

```tsx
<DialogClose>
  <Button type="button" variant="ghost">Cancel</Button>
</DialogClose>
```

## Form Pattern

Uses custom `Form` component (no @radix-ui dependency):

```tsx
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";

<Form {...form}>
  <FormField
    control={form.control}
    name="fieldName"
    render={({ field }) => (
      <FormItem>
        <FormLabel>Label</FormLabel>
        <FormControl>
          <Input {...field} />
        </FormControl>
        <FormMessage />
      </FormItem>
    )}
  />
</Form>
```

## Input Styling (Dark Dashboard)

```tsx
<Input className="bg-white/4 border-white/8 focus:border-white/15 focus:ring-0" />
<Textarea className="bg-white/4 border-white/8 font-mono text-xs" />
```

## Badge Patterns

```tsx
// Status badges
<Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/20">Active</Badge>
<Badge className="bg-white/8 text-white/50 border-white/10">Draft</Badge>
```

## Available Components
button, input, textarea, card, dialog, sheet, dropdown-menu, badge, skeleton, select, form, label, avatar, scroll-area, sonner (toast)
