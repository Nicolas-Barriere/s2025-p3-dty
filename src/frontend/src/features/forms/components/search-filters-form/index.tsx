import { SearchHelper } from "@/features/utils/search-helper";
import { Label } from "@gouvfr-lasuite/ui-kit";
import { Button, Checkbox, Input, Select } from "@openfun/cunningham-react";
import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { fetchAPI } from "@/features/api/fetch-api";
import { useRouter } from "next/router";
import { usePathname } from "next/navigation";

/**
 * SearchFiltersForm component for email search with chatbot integration
 * 
 * This component provides a form interface for filtering emails with various criteria.
 * It includes special handling for the ChatbotSearchInput component to enable intelligent search.
 * 
 * Key features:
 * 1. Handles traditional email filtering (from, to, subject, text)
 * 2. Special handling for message_ids from RAG search results
 * 3. Directly updates URL and reloads when RAG results are available
 * 4. Converts form fields into a query string for the mailbox search API
 */

type SearchFiltersFormProps = {
    query: string;
    onChange: (query: string, submit: boolean) => void;
}

export const SearchFiltersForm = ({ query, onChange }: SearchFiltersFormProps) => {
    const { t, i18n } = useTranslation();
    const router = useRouter();
    const pathname = usePathname();
    const formRef = useRef<HTMLFormElement>(null);

    const updateQuery = async (submit: boolean) => {
        const formData = new FormData(formRef.current as HTMLFormElement);
        const chatbotQuery = formData.get('chatbot');
        // If chatbot field is filled, use Albert API for advanced search
        if (submit && chatbotQuery && String(chatbotQuery).trim() !== "") {
            // Call Albert API
            const intelligentSearchRes = await fetchAPI<{ success: boolean; results?: Array<{ id: string }>; error?: string; }>(
                "/api/v1.0/chatbot/intelligent-search/",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query: chatbotQuery }),
                }
            );
            const actualResponse = (intelligentSearchRes as any)?.data || intelligentSearchRes;
            if (actualResponse?.success && actualResponse?.results && actualResponse.results.length > 0) {
                // Build message_ids param and update URL using router (no page reload)
                const mailIds = actualResponse.results.map((r: any) => r.id).join(',');
                const newSearchParams = new URLSearchParams();
                newSearchParams.set('message_ids', mailIds);
                
                // Use router navigation instead of window.location.reload()
                router.replace(pathname + '?' + newSearchParams.toString(), undefined, { shallow: true });
                return;
            } else {
                // Show error or fallback to classic search
                alert(actualResponse?.error || "Aucun résultat trouvé par le chatbot.");
                return;
            }
        }
        // Otherwise, classic search
        const query = SearchHelper.serializeSearchFormData(formData, i18n.language);
        onChange(query, submit);
        formRef.current?.reset();
    }

    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        updateQuery(true);
    };
    const handleChange = () => updateQuery(false);

    const handleReset = () => {
        onChange('', false);
        formRef.current?.reset();
    }

    const parsedQuery = SearchHelper.parseSearchQuery(query);

    const handleReadStateChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const { name, checked } = event.target;
        if (checked) {
            const checkboxToUncheck = formRef.current?.elements.namedItem(name === "is_read" ? "is_unread" : "is_read") as HTMLInputElement;
            if (checkboxToUncheck) {
                checkboxToUncheck.checked = false;
            }
        }
    }

    return (
        <form className="search__filters" ref={formRef} onSubmit={handleSubmit} onChange={handleChange}>
            <Input
                name="from"
                label={t("search.filters.label.from")}
                value={parsedQuery.from as string}
                fullWidth
            />
            <Input
                name="to"
                label={t("search.filters.label.to")}
                value={parsedQuery.to as string}
                fullWidth
            />
            <Input
                name="subject"
                label={t("search.filters.label.subject")}
                value={parsedQuery.subject as string}
                fullWidth
            />
            <Input
                name="text"
                label={t("search.filters.label.text")}
                value={parsedQuery.text as string}
                fullWidth
            />
            <Input
                name="chatbot"
                label={t("search.filters.label.chatbot")}
                value={parsedQuery.chatbot as string}
                fullWidth
            />
            <Select
                name="in"
                label={t("search.filters.label.in")}
                value={parsedQuery.in as string ?? 'all'}
                showLabelWhenSelected={false}
                onChange={handleChange}
                options={[
                    {
                        label: t("folders.all_messages"),
                        render: () => <FolderOption label={t("folders.all_messages")} icon="folder" />,
                        value: 'all'
                    },
                    {
                        label: t("folders.drafts"),
                        render: () => <FolderOption label={t("folders.drafts")} icon="drafts" />,
                        value: "draft"
                    },
                    {
                        label: t("folders.sent"),
                        render: () => <FolderOption label={t("folders.sent")} icon="outbox" />,
                        value: "sent"
                    },
                    {
                        label: t("folders.trash"),
                        render: () => <FolderOption label={t("folders.trash")} icon="delete" />,
                        value: "trash" },
                ]}
                clearable={false}
                fullWidth
            />
            <div className="flex-row flex-align-center" style={{ gap: 'var(--c--theme--spacings--2xs)' }}>
                <Label>{t("search.filters.label.read_state")} :</Label>
                <Checkbox label={t("search.filters.label.read")} value="true" name="is_read" checked={Boolean(parsedQuery.is_read)} onChange={handleReadStateChange} />
                <Checkbox label={t("search.filters.label.unread")} value="true" name="is_unread" checked={Boolean(parsedQuery.is_unread)} onChange={handleReadStateChange} />
            </div>
            <footer className="search__filters-footer">
                <Button type="reset" color="tertiary-text" onClick={handleReset}>
                    {t("search.filters.reset")}
                </Button>
                <Button type="submit" color="tertiary">
                    {t("search.filters.submit")}
                </Button>
            </footer>
        </form>
    );
};

type FolderOptionProps = {
    label: string;
    icon: string;
}

const FolderOption = ({ label, icon }: FolderOptionProps) => {
    return (
        <div className="search__filters-folder-option">
            <span className="material-icons">{icon}</span>
            {label}
        </div>
    );
}