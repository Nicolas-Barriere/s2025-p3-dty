import { Attachment } from "@/features/api/gen/models/attachment";
import { AttachmentItem } from "./attachment-item";
import { useTranslation } from "react-i18next";
import { AttachmentHelper } from "@/features/utils/attachment-helper";
type AttachmentListProps = {
    attachments: readonly Attachment[]
}

export const AttachmentList = ({ attachments }: AttachmentListProps) => {
    const { t, i18n } = useTranslation();

    return (
        <section className="thread-attachment-list">
            <header className="thread-attachment-list__header">
                <p>
                    <strong>{t("attachments.counter", { count: attachments.length })}</strong>
                    {' '}
                    ({AttachmentHelper.getFormattedTotalSize(attachments, i18n.resolvedLanguage)})
                </p>
            </header>
            <div className="thread-attachment-list__body">
                {attachments.map((attachment) => <AttachmentItem key={attachment.id} attachment={attachment} />)}
            </div>
        </section>
    )
}
