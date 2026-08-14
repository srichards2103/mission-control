"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

/* Dense data table: ~38px rows, hairline dividers, 12px muted header labels.
   Numeric columns take `className="num text-right"` on both head and cell.
   Row actions live in a `<RowActions>` cell and appear only on row hover. */

function Table({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <div
      data-slot="table-container"
      className="relative w-full overflow-x-auto"
    >
      <table
        data-slot="table"
        className={cn("w-full caption-bottom border-y text-sm", className)}
        {...props}
      />
    </div>
  )
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return (
    <thead
      data-slot="table-header"
      className={cn("[&_tr]:border-b [&_tr]:hover:bg-transparent", className)}
      {...props}
    />
  )
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return (
    <tbody
      data-slot="table-body"
      className={cn("[&_tr:last-child]:border-0", className)}
      {...props}
    />
  )
}

function TableFooter({ className, ...props }: React.ComponentProps<"tfoot">) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn("border-t font-medium [&>tr]:last:border-b-0", className)}
      {...props}
    />
  )
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        "group/row border-b transition-colors hover:bg-muted/40 has-aria-expanded:bg-muted/40 data-[state=selected]:bg-muted",
        className
      )}
      {...props}
    />
  )
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        "h-8 px-3 text-left align-middle text-xs font-medium whitespace-nowrap text-muted-foreground first:pl-0 last:pr-0 [&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  )
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return (
    <td
      data-slot="table-cell"
      className={cn(
        "h-[38px] px-3 py-0 align-middle whitespace-nowrap first:pl-0 last:pr-0 [&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  )
}

/* Right-aligned actions cell whose content is revealed on row hover (and on
   keyboard focus within, so the controls stay reachable without a mouse). */
function RowActions({ className, children, ...props }: React.ComponentProps<"td">) {
  return (
    <td
      data-slot="table-cell"
      className={cn("h-[38px] px-3 py-0 text-right align-middle whitespace-nowrap last:pr-0", className)}
      {...props}
    >
      <div className="inline-flex items-center justify-end gap-1.5 opacity-0 transition-opacity group-hover/row:opacity-100 has-focus-visible:opacity-100 has-aria-expanded:opacity-100">
        {children}
      </div>
    </td>
  )
}

function TableCaption({
  className,
  ...props
}: React.ComponentProps<"caption">) {
  return (
    <caption
      data-slot="table-caption"
      className={cn("mt-4 text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  RowActions,
  TableCaption,
}
