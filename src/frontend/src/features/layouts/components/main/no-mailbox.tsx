import { Button } from "@openfun/cunningham-react"
import { logout } from "@/features/auth";
import { useTranslation } from "react-i18next";

export const NoMailbox = () => {
    const { t } = useTranslation();
    return (
        <div className="no-mailbox">
            <div>
                <span className="material-icons">error</span>
                <p>{t('no_mailbox')}</p>
                <Button onClick={logout}>{t('user_menu.logout')}</Button>
            </div>
        </div>
    )
}
