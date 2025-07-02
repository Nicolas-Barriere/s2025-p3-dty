import React from "react";
import {
  useThreadsSummaryRetrieve,
  useThreadsRefreshSummaryCreate,
  threadsSummaryRetrieveResponse200,
} from "@/features/api/gen";
import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";
import { addToast, ToasterItem } from "@/features/ui/components/toaster";

export const ThreadSummary = ({ threadId }: { threadId: string }) => {
  const { data, isLoading, error, refetch } =
    useThreadsSummaryRetrieve<threadsSummaryRetrieveResponse200>(threadId);

  const summary = data?.data.summary?.trim();

  const refreshMutation = useThreadsRefreshSummaryCreate({
    mutation: {
      onMutate: () => {
        addToast(
          <ToasterItem type="info">Génération du résumé en cours ...</ToasterItem>
        );
        refetch();
      },
      onSuccess: () => {
        addToast(<ToasterItem type="info">Résumé mis à jour !</ToasterItem>);
        refetch();
      },
      onError: () => {
        addToast(
          <ToasterItem type="error">
            Erreur lors de la mise à jour du résumé.
          </ToasterItem>
        );
      },
    },
  });

  const handleRefresh = () => {
    refreshMutation.mutate({ id: threadId });
  };

  return (
    <div className="thread-summary__container">
      <h3>Résumé du Thread</h3>

      {isLoading ? (
        <Spinner />
      ) : error ? (
        <p>Erreur de chargement du résumé.</p>
      ) : (
        <>
          <div className="thread-summary__content">
            <p>{summary || "Aucun résumé disponible."}</p>
          </div>
          <div className="thread-summary__actions">
            <Button
              color="primary"
              icon={<span className="material-icons">auto_awesome</span>}
              onClick={handleRefresh}
            >
              {refreshMutation.isPending
                ? "Traitement en cours..."
                : summary
                  ? "Mettre à jour le résumé"
                  : "Générer le résumé"}
            </Button>
          </div>
        </>
      )}
    </div>
  );
};
