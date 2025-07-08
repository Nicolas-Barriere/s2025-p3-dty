import { useMailboxContext } from "@/features/providers/mailbox";
import Bar from "@/features/ui/components/bar";
import { Button, Tooltip } from "@openfun/cunningham-react"
import { useTranslation } from "react-i18next";


export const ActionBar = () => {
    const { t } = useTranslation();
    const { unselectThread } = useMailboxContext();

    return (
        <Bar className="thread-action-bar">
            <div className="thread-action-bar__left">
                <Tooltip content={t('actions.close_thread')}>
                    <Button
                        onClick={unselectThread}
                        color="tertiary-text"
                        aria-label={t('tooltips.close_thread')}
                        size="small"
                        icon={<span className="material-icons">close</span>}
                    />
                </Tooltip>
            </div>
            <div className="thread-action-bar__right">
                <Tooltip content={t('actions.mark_as_unread')}>
                    <Button
                        color="primary-text"
                        aria-label={t('actions.mark_as_unread')}
                        size="small"
                        icon={<span className="material-icons">mark_email_unread</span>}
                        onClick={() => {
                            // Mark as unread functionality would go here
                        }}
                    />
                </Tooltip>
            </div>
        </Bar>
    )
}
