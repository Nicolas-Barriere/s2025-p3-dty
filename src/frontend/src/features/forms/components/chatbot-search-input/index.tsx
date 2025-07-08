import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { fetchAPI } from "@/features/api/fetch-api";
import styles from "./ChatbotSearchInput.module.css";

type ChatbotSearchInputProps = {
    name: string;
    label: string;
    value?: string;
    fullWidth?: boolean;
    onChange?: (value: { [key: string]: string }) => void;
}

export const ChatbotSearchInput = ({ 
    name, 
    label, 
    value = "", 
    fullWidth = false,
    onChange 
}: ChatbotSearchInputProps) => {
    const { t } = useTranslation();
    const [input, setInput] = useState(value);
    const [isLoading, setIsLoading] = useState(false);
    const [response, setResponse] = useState("");
    const [showCopyToast, setShowCopyToast] = useState(false);

    const sendToChatbot = useCallback(async () => {
        if (!input.trim() || isLoading) return;

        setIsLoading(true);
        setResponse("");

        try {
            // First, try intelligent search for comprehensive AI-powered email analysis
            const intelligentSearchRes = await fetchAPI<{
                success: boolean;
                results?: Array<{
                    id: string;
                    subject: string;
                    sender: { email: string };
                    snippet?: string;
                    [key: string]: unknown;
                }>;
                search_summary?: string;
                total_matches?: number;
                total_emails?: number;
                query?: string;
                error?: string;
            }>("/mails/chatbot/intelligent-search/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: input.trim()
                }),
            });

            if (intelligentSearchRes.success && intelligentSearchRes.results && intelligentSearchRes.results.length > 0) {
                // We have intelligent search results - format them nicely
                const resultsCount = intelligentSearchRes.total_matches || intelligentSearchRes.results.length;
                const totalEmails = intelligentSearchRes.total_emails || 0;
                
                let responseText = `🔍 Recherche intelligente: ${resultsCount} email(s) pertinent(s) trouvé(s) sur ${totalEmails} emails analysés.\n\n`;
                
                if (intelligentSearchRes.search_summary) {
                    responseText += intelligentSearchRes.search_summary;
                } else {
                    // If no summary, create one from the results
                    responseText += "Voici les emails les plus pertinents trouvés :\n";
                    intelligentSearchRes.results.slice(0, 3).forEach((result, index) => {
                        responseText += `\n${index + 1}. ${result.subject || 'Email sans objet'}\n`;
                        if (result.from) responseText += `   De: ${result.from}\n`;
                        if (result.date && typeof result.date === 'string') responseText += `   Date: ${new Date(result.date).toLocaleDateString('fr-FR')}\n`;
                        if (result.snippet) responseText += `   Aperçu: ${result.snippet.substring(0, 100)}...\n`;
                    });
                }
                
                setResponse(responseText);

                // Trigger mailbox search with the received email IDs
                if (onChange) {
                    const mailIds = intelligentSearchRes.results.map(r => r.id).join(',');
                    if (mailIds) {
                        onChange({ ids: mailIds });
                    }
                }
            } else {
                // If intelligent search doesn't return results, show appropriate message
                const errorMessage = intelligentSearchRes.error || "Aucun résultat trouvé";
                setResponse(`Désolé, je n'ai pas pu trouver d'emails correspondants: ${errorMessage}`);
            }
        } catch (error) {
            console.error('Chatbot search error:', error);
            setResponse("Erreur lors de la communication avec le chatbot. Veuillez réessayer.");
        } finally {
            setIsLoading(false);
        }
    }, [input, isLoading, onChange]);

    const handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            sendToChatbot();
        }
    };

    return (
        <div className={`${styles.chatbotSearchInput} ${fullWidth ? styles.fullWidth : ''}`}>
            <label htmlFor={name} className={styles.label}>
                {label}
            </label>
            <div className={styles.inputContainer}>
                <input
                    id={name}
                    name={name}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={t("search.filters.chatbot.placeholder", "Demandez au chatbot de vous aider à rechercher...")}
                    className={styles.input}
                    disabled={isLoading}
                />
                <button
                    type="button"
                    onClick={sendToChatbot}
                    disabled={isLoading || !input.trim()}
                    className={styles.button}
                    title={t("search.filters.chatbot.send", "Envoyer au chatbot")}
                >
                    {isLoading ? (
                        <span className={styles.loading}>⟳</span>
                    ) : (
                        <span className="material-icons">smart_toy</span>
                    )}
                </button>
            </div>
            
            {/* Examples section */}
            {!input && !response && (
                <div className={styles.examples}>
                    <div className={styles.examplesTitle}>
                        💡 {t("search.filters.chatbot.examples_title", "Exemples d'utilisation")}:
                    </div>
                    <div className={styles.examplesList}>
                        <button 
                            type="button" 
                            className={styles.exampleButton}
                            onClick={() => setInput("emails urgents de Marie cette semaine")}
                        >
                            &ldquo;emails urgents de Marie cette semaine&rdquo;
                        </button>
                        <button 
                            type="button" 
                            className={styles.exampleButton}
                            onClick={() => setInput("documents PDF avec factures")}
                        >
                            &ldquo;documents PDF avec factures&rdquo;
                        </button>
                        <button 
                            type="button" 
                            className={styles.exampleButton}
                            onClick={() => setInput("emails non lus de la semaine dernière")}
                        >
                            &ldquo;emails non lus de la semaine dernière&rdquo;
                        </button>
                        <button 
                            type="button" 
                            className={styles.exampleButton}
                            onClick={() => setInput("réunions et rendez-vous importants")}
                        >
                            &ldquo;réunions et rendez-vous importants&rdquo;
                        </button>
                    </div>
                </div>
            )}
            
            {response && (
                <div className={styles.response}>
                    <div className={styles.responseHeader}>
                        <span className="material-icons">smart_toy</span>
                        <span>{t("search.filters.chatbot.response", "Réponse du chatbot")}</span>
                        <button
                            type="button"
                            className={styles.copyButton}
                            onClick={async () => {
                                try {
                                    await navigator.clipboard.writeText(response);
                                    setShowCopyToast(true);
                                    setTimeout(() => setShowCopyToast(false), 2000);
                                } catch (err) {
                                    console.error('Failed to copy text:', err);
                                }
                            }}
                            title={t("search.filters.chatbot.copy", "Copier la requête")}
                        >
                            <span className="material-icons">content_copy</span>
                        </button>
                    </div>
                    <div className={styles.responseText}>
                        {response}
                    </div>
                </div>
            )}
            
            {/* Copy toast notification */}
            {showCopyToast && (
                <div className={styles.copyToast}>
                    <span className="material-icons">check_circle</span>
                    {t("search.filters.chatbot.copy_success", "Requête copiée !")}
                </div>
            )}
        </div>
    );
};
