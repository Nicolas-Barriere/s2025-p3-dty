import { useEffect, useState } from "react";
import { Button } from "@openfun/cunningham-react";
import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { addToast, ToasterItem } from "@/features/ui/components/toaster";
import ReactMarkdown from "react-markdown";
import { useThreadsRefreshSummaryCreate } from "@/features/api/gen";


interface ThreadSummaryProps {
  threadId: string;
  summary: string;
  onSummaryUpdated?: (newSummary: string) => void;
}

export const ThreadSummary = ({ threadId, summary, onSummaryUpdated }: ThreadSummaryProps) => {
  const [localSummary, setLocalSummary] = useState(summary);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshMutation = useThreadsRefreshSummaryCreate({
    mutation: {
      onMutate: () => {
        setIsRefreshing(true);
        addToast(
          <ToasterItem type="info">
            Génération du résumé en cours ...
          </ToasterItem>
        );
      },
      onSuccess: (data) => {
        // Type guard for API response
        const newSummary = (data && typeof data === 'object' && 'data' in data && data.data && typeof data.data === 'object' && 'summary' in data.data)
          ? (data.data as { summary?: string }).summary
          : undefined;
        if (newSummary) {
          setLocalSummary(newSummary);
          if (onSummaryUpdated) {
            onSummaryUpdated(newSummary);
          }
          addToast(<ToasterItem type="info">Résumé mis à jour !</ToasterItem>);
        }
        setIsRefreshing(false);
      },
      onError: () => {
        addToast(
          <ToasterItem type="error">
            Erreur lors de la mise à jour du résumé.
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
    if (summary) {
      setLocalSummary(summary);
    }
  }, [summary]);

  return (
    <div className="thread-summary__container">
      <h3>
        Résumé du Thread <span className="material-icons">autorenew</span>
      </h3>

      {isRefreshing ? (
        <div className="thread-summary__loading">
          <Spinner />
        </div>
      ) : (
        <>
          <div className="thread-summary__content">
            {localSummary ? (
              <ReactMarkdown>{localSummary}</ReactMarkdown>
            ) : (
              <p>Aucun résumé disponible.</p>
            )}
          </div>
          <div className="thread-summary__actions">
            <Button
              color="primary"
              icon={<span className="material-icons">summarize</span>}
              onClick={handleRefresh}
            >
              Mettre à jour le résumé
            </Button>
          </div>
        </>
      )}
    </div>
  );
};
