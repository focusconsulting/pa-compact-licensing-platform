import { useTranslation } from "react-i18next";
import {
  StepIndicator as UswdsStepIndicator,
  StepIndicatorStep,
  type HeadingLevel,
} from "@trussworks/react-uswds";

export interface StepIndicatorProps {
  /** Each step's name, in order. */
  steps: string[];
  /** The current step's index, from 0. */
  current: number;
  /** Defaults to `h2`: the indicator sits above the page's `h1` (B2). */
  headingLevel?: HeadingLevel;
}

function stepStatus(index: number, current: number) {
  if (index < current) return "complete";
  if (index === current) return "current";
  return "incomplete";
}

/** Where the user is in a form split into steps (B2, B6). */
export default function StepIndicator({
  steps,
  current,
  headingLevel = "h2",
}: StepIndicatorProps) {
  const { t } = useTranslation("common");
  const statusText = {
    complete: t("stepIndicator.complete"),
    incomplete: t("stepIndicator.incomplete"),
  };
  return (
    <UswdsStepIndicator
      headingLevel={headingLevel}
      stepText={t("stepIndicator.step")}
      ofText={t("stepIndicator.of")}
      statusText={statusText}
    >
      {steps.map((label, index) => (
        <StepIndicatorStep
          key={label}
          label={label}
          statusText={statusText}
          status={stepStatus(index, current)}
        />
      ))}
    </UswdsStepIndicator>
  );
}
