interface Props {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ icon = "📭", title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
      <div className="text-5xl">{icon}</div>
      <div>
        <p className="text-lg font-semibold text-surface-700">{title}</p>
        {description && <p className="text-sm text-surface-500 mt-1 max-w-sm">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
