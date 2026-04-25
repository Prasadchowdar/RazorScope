import Badge from "./Badge";

interface Props {
  score: number;
  label: "high" | "medium" | "low";
  showScore?: boolean;
}

export default function RiskBadge({ score, label, showScore = false }: Props) {
  const variant = label === "high" ? "negative" : label === "medium" ? "warning" : "positive";
  const prefix = label === "high" ? "High" : label === "medium" ? "Med" : "Low";
  return (
    <Badge variant={variant} size="xs">
      {showScore ? `${prefix} ${score}` : prefix}
    </Badge>
  );
}
