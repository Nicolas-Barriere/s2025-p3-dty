import { useMutation } from '@tanstack/react-query';
import { Button, Tooltip } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { fetchAPI } from "@/features/api/fetch-api";

/**
 * Component for the "Generate Response" button
 * This button sends a request to the AI to generate a response to the current email
 */
interface GenerateResponseButtonProps {
  messageId: string;
  mailboxId: string;
  replyAll?: boolean;
  isLatest: boolean;
  disabled?: boolean;
  onSuccess?: (draftId: string, threadId: string) => void;
}

const GenerateResponseButton = ({ 
  messageId, 
  mailboxId, 
  replyAll = false, 
  isLatest = false,
  disabled = false,
  onSuccess 
}: GenerateResponseButtonProps) => {
  const { t } = useTranslation();

  // Mutation to call the backend API
  const generateResponseMutation = useMutation({
    mutationFn: async () => {
      const response = await fetchAPI<{
        data: { success: boolean; draft_id: string; thread_id: string; message?: string; error?: string; }
      }>('/api/answer_generator/generate-email-response/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message_id: messageId,
          mailbox_id: mailboxId,
          reply_all: replyAll,
        }),
      });

      return response.data;
    },
    onSuccess: (data) => {
      if (data.success && onSuccess) {
        onSuccess(data.draft_id, data.thread_id);
      }
    },
  });

  // Only show button for latest message and not for drafts
  if (!isLatest) {
    return null;
  }

  return (
    <Button
      color="secondary"
      icon={<span className="material-icons">auto_awesome</span>}
      aria-label={t('actions.generate_response')}
      onClick={() => generateResponseMutation.mutate()}
      disabled={disabled || generateResponseMutation.isPending}
      data-testid="generate-response-button"
    >
      {generateResponseMutation.isPending ? (
        <span>{t('actions.generating')}</span>
      ) : (
        <span>{t('actions.generate_response')}</span>
      )}
    </Button>
  );
};

export default GenerateResponseButton;
