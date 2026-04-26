interface Props {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorBanner({ message = "Something went wrong.", onRetry }: Props) {
  return (
    <div className="alert-banner-error">
      <span className="text-lg shrink-0">⚠️</span>
      <div className="flex-1">
        <p className="font-medium">Error</p>
        <p className="text-sm opacity-90">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="btn btn-sm border border-danger-dark text-danger-dark hover:bg-danger-light">
          Retry
        </button>
      )}
    </div>
  );
}
