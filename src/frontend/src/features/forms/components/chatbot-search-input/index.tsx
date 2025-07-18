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

/**
 * ChatbotSearchInput component for intelligent email search
 * 
 * This component provides an interface for users to search their emails using natural language queries.
 * It connects to the Albert API for RAG (Retrieval Augmented Generation) search capabilities.
 * 
 * The component:
 * 1. Sends user queries to the /api/v1.0/deep_search/intelligent-search/ endpoint
 * 2. Displays a summary of search results to the user
 * 3. Triggers a mailbox search with the message IDs returned from the RAG system
 * 4. Uses the message_ids parameter for direct mailbox filtering without polluting the text search
 */
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
            }>("/api/v1.0/deep_search/intelligent-search/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: input.trim()
                }),
            });

            // The fetchAPI wraps the response in { status, data, headers }
            // So we need to extract the actual data
            const actualResponse = (intelligentSearchRes as { data?: typeof intelligentSearchRes })?.data || intelligentSearchRes;
            
            // Minimal logs for troubleshooting - conditional for production
            if (process.env.NODE_ENV !== 'production') {
                console.warn('RAG search:', actualResponse?.success ? 'successful' : 'failed');
            }

            if (actualResponse?.success && actualResponse?.results && actualResponse.results.length > 0) {
                // We have intelligent search results - format them nicely
                const resultsCount = actualResponse.total_matches || actualResponse.results.length;
                const totalEmails = actualResponse.total_emails || 0;
                
                let responseText = `🔍 Recherche intelligente: ${resultsCount} email(s) pertinent(s) trouvé(s) sur ${totalEmails} emails analysés.\n\n`;
                
                if (actualResponse.search_summary) {
                    responseText += actualResponse.search_summary;
                } else {
                    // If no summary, create one from the results
                    responseText += "Voici les emails les plus pertinents trouvés :\n";
                    actualResponse.results.slice(0, 3).forEach((result: { subject?: string; from?: string; date?: string; snippet?: string }, index: number) => {
                        responseText += `\n${index + 1}. ${result.subject || 'Email sans objet'}\n`;
                        if (result.from) responseText += `   De: ${result.from}\n`;
                        if (result.date && typeof result.date === 'string') responseText += `   Date: ${new Date(result.date).toLocaleDateString('fr-FR')}\n`;
                        if (result.snippet) responseText += `   Aperçu: ${result.snippet.substring(0, 100)}...\n`;
                    });
                }
                
                setResponse(responseText);

                // Trigger mailbox search with the received email IDs
                if (onChange) {
                    const mailIds = actualResponse.results.map((r: { id: string }) => r.id).join(',');
                    
                    if (mailIds) {
                        // Use message_ids parameter for direct search instead of text search
                        // Only pass the message_ids without any text to avoid populating the search box
                        onChange({ message_ids: mailIds });
                    } else {
                        console.error('No email IDs found in search results');
                    }
                } else {
                    console.error('No onChange callback provided');
                }
            } else {
                // If intelligent search doesn't return results, show appropriate message
                const errorMessage = actualResponse?.error || "Aucun résultat trouvé";
                setResponse(`Désolé, je n'ai pas pu trouver d'emails correspondants: ${errorMessage}`);
            }
        } catch (error) {
            console.error('Chatbot search error:', error instanceof Error ? error.message : String(error));
            setResponse("Erreur lors de la communication avec le chatbot. Veuillez réessayer.");
        } finally {
            setIsLoading(false);
        }
    }, [input, isLoading, onChange]);

    const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
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
                    onKeyDown={handleKeyDown}
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
