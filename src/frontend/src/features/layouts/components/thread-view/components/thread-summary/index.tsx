import { useEffect, useState } from "react";
import { Button, Tooltip } from "@openfun/cunningham-react";
import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { addToast, ToasterItem } from "@/features/ui/components/toaster";
import ReactMarkdown from "react-markdown";
import { useThreadsRefreshSummaryCreate } from "@/features/api/gen";
import { useTranslation } from "react-i18next";

interface ThreadSummaryProps {
  threadId: string;
  summary: string;
  onSummaryUpdated?: (newSummary: string) => void;
}

export const ThreadSummary = ({
  threadId,
  summary,
  onSummaryUpdated,
}: ThreadSummaryProps) => {
  const { t } = useTranslation();
  const [localSummary, setLocalSummary] = useState(summary);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshMutation = useThreadsRefreshSummaryCreate({
    mutation: {
      onMutate: () => {
        setIsRefreshing(true);
        addToast(
          <ToasterItem type="info">
            {t("summary.generation_in_progress")}
          </ToasterItem>
        );
      },
      onSuccess: (data) => {
        // Type guard for API response
        const newSummary =
          data &&
          typeof data === "object" &&
          "data" in data &&
          data.data &&
          typeof data.data === "object" &&
          "summary" in data.data
            ? (data.data as { summary?: string }).summary
            : undefined;
        if (newSummary) {
          setLocalSummary(newSummary);
          if (onSummaryUpdated) {
            onSummaryUpdated(newSummary);
          }
          addToast(<ToasterItem type="info">{t("summary.refresh_success")}</ToasterItem>);
        }
        setIsRefreshing(false);
      },
      onError: () => {
        addToast(
          <ToasterItem type="error">
            {t("summary.refresh_error")}
          </ToasterItem>
        );
        setIsRefreshing(false);
      },
    },
  });

  const handleRefresh = () => {
    refreshMutation.mutate({ id: threadId });
  };

  useEffect(() => {
    setLocalSummary(summary);
  }, [summary]);

  return (
    <div className="thread-summary__container">
      {isRefreshing ? (
        <div className="thread-summary__content">
          <Spinner />
        </div>
      ) : (
        <>
          <div className="thread-summary__content">
            {localSummary ? (
              <ReactMarkdown>{`**${t("summary.title")} :** ${localSummary}`}</ReactMarkdown>
            ) : (
              <p>{t("summary.no_summary")}</p>
            )}
          </div>
          <div className="thread-summary__refresh-button">
            <Tooltip content={t("actions.refresh_summary")}>
              <Button
                color="tertiary-text"
                size="small"
                icon={<span className="material-icons">autorenew</span>}
                aria-label={t("actions.refresh_summary")}
                onClick={handleRefresh}
              />
            </Tooltip>
          </div>
        </>
      )}
    </div>
  );
};
