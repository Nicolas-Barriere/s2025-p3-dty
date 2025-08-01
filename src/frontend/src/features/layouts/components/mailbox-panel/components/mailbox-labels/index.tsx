import { TreeLabel, useLabelsList } from "@/features/api/gen";
import { Icon, IconType, Spinner } from "@gouvfr-lasuite/ui-kit";
import { Button, useModal, Tooltip } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { LabelModal } from "./components/label-form-modal";
import { LabelItem } from "./components/label-item";
import { useState } from "react";

type MailboxLabelsProps = {
  mailboxId: string;
}

export const MailboxLabels = ({ mailboxId }: MailboxLabelsProps) => {
  const { t } = useTranslation();
  const { isOpen, onClose, open } = useModal();
  const [labelToEdit, setLabelToEdit] = useState<TreeLabel | undefined>(undefined);
  const labelsQuery = useLabelsList({ mailbox_id: mailboxId })

  const editLabel = (label: TreeLabel) => {
    setLabelToEdit(label)
    open()
  }

  const handleClose = () => {
    setLabelToEdit(undefined)
    onClose()
  }

  return (
    <section className="mailbox-labels">
      <header className="mailbox-labels__header">
        <p className="mailbox-labels__title">{t('labels.title')}</p>
        {labelsQuery.isLoading ? <Spinner /> : (
          <Tooltip content={t('labels.create')} placement="left">
            <Button
              icon={<Icon type={IconType.FILLED} name="add" />}
              color="tertiary-text"
              size="small"
              onClick={open}
              className="mailbox-labels__create-button"
              aria-label={t('labels.create')}
            />
          </Tooltip>
        )}
      </header>
      <div className="label-list">
        {
            labelsQuery.data?.data.map((label) => (
              <LabelItem key={label.id} {...label} onEdit={editLabel} />
            ))
        }
      </div>
      <LabelModal isOpen={isOpen} onClose={handleClose} label={labelToEdit} />
    </section>
  )
}
