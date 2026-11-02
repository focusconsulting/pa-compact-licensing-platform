import { ReactNode } from "react";
import { Table } from "@trussworks/react-uswds";

export interface Column<T> {
  key: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  /** The table's name for screen readers; the heading above it already shows it on screen. */
  caption: string;
}

/**
 * A bordered USWDS table of records, as C3 and C4 draw them. The first column
 * heads each row, so a screen reader names the record with every cell; it is
 * styled as a plain cell, as drawn.
 */
export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  caption,
}: DataTableProps<T>) {
  const [first, ...rest] = columns;
  return (
    <Table
      bordered
      fullWidth
      caption={<span className="usa-sr-only">{caption}</span>}
    >
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column.key} scope="col">
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={rowKey(row)}>
            <th scope="row" className="bg-white text-normal">
              {first.cell(row)}
            </th>
            {rest.map((column) => (
              <td key={column.key}>{column.cell(row)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
