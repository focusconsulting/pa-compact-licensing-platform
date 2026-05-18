import { ReactNode } from "react";
import { FormProvider, useForm, UseFormProps } from "react-hook-form";
import { render, RenderOptions } from "@testing-library/react";

interface FormWrapperProps {
  children: ReactNode;
  onSubmit?: (data: Record<string, unknown>) => void;
  defaultValues?: Record<string, unknown>;
}

function FormWrapperComponent({
  children,
  onSubmit,
  defaultValues,
}: FormWrapperProps) {
  const methods = useForm({ defaultValues });
  return (
    <FormProvider {...methods}>
      <form onSubmit={methods.handleSubmit((data) => onSubmit?.(data))}>
        {children}
        <button type="submit">Submit</button>
      </form>
    </FormProvider>
  );
}

export function renderWithForm(
  ui: ReactNode,
  options?: {
    defaultValues?: Record<string, unknown>;
    onSubmit?: (data: Record<string, unknown>) => void;
    renderOptions?: RenderOptions;
  },
) {
  return render(
    <FormWrapperComponent
      defaultValues={options?.defaultValues}
      onSubmit={options?.onSubmit}
    >
      {ui}
    </FormWrapperComponent>,
    options?.renderOptions,
  );
}
