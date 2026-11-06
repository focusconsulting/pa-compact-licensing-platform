import type { Meta, StoryObj } from "@storybook/nextjs";
import { ReactNode } from "react";
import { FormProvider, useForm } from "react-hook-form";

import { FilePickerField } from "./FilePickerField";

function Form({
  children,
  defaultValues,
}: {
  children: ReactNode;
  defaultValues?: Record<string, unknown>;
}) {
  const methods = useForm({ defaultValues });
  return (
    <FormProvider {...methods}>
      <form>{children}</form>
    </FormProvider>
  );
}

const meta: Meta<typeof FilePickerField> = {
  title: "Components/FilePickerField",
  component: FilePickerField,
  args: {
    id: "certificate",
    label: "NCCPA certificate",
    kind: "nccpa_certificate",
    hint: "PDF, PNG, JPEG, CSV, or Word (.docx), up to 20 MB",
    accept: ".pdf,.png,.jpg,.jpeg,.csv,.docx",
  },
  decorators: [
    (Story) => (
      <Form>
        <Story />
      </Form>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof FilePickerField>;

/**
 * Nothing chosen yet. Against the Prism mock (`just mock-api`) a chosen file
 * gets the example upload form, whose storage URL does not exist, so the
 * field ends in its "could not be uploaded" state.
 */
export const Empty: Story = {};

/** A document the form already holds, such as on returning to a saved step. */
export const Uploaded: Story = {
  decorators: [
    (Story) => (
      <Form
        defaultValues={{
          certificate: {
            id: "0b9c7a52-4f1e-4d38-9f43-2a5d6f1c8e70",
            fileName: "nccpa-certificate.pdf",
          },
        }}
      >
        <Story />
      </Form>
    ),
  ],
};
