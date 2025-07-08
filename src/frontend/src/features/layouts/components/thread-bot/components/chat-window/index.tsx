import { useState } from "react"
import styles from "./ChatWindow.module.css"
import { fetchAPI } from "@/features/api/fetch-api";
import ReactMarkdown from 'react-markdown';

export const ChatWindow = () => {
    type ChatMessage = {
        role: "user" | "bot";
        text: string;
        type?: string;
        function_used?: string;
        timestamp?: Date;
    }

    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            role: "bot",
            text: "👋 Bonjour ! Je suis votre assistant email intelligent. Je peux vous aider à :\n\n• 📧 Résumer des emails\n• ✉️ Générer des réponses\n• 🏷️ Classer des emails\n• 💬 Répondre à vos questions\n\nComment puis-je vous aider aujourd'hui ?",
            type: "conversation",
            timestamp: new Date()
        }
    ])
    const [input, setInput] = useState("")
    const [isLoading, setIsLoading] = useState(false)

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return

        const userMsg: ChatMessage = {
            role: "user",
            text: input,
            timestamp: new Date()
        }
        setMessages(prev => [...prev, userMsg])
        setInput("")
        setIsLoading(true)

        try {
            // Build conversation history for context
            const conversationHistory = messages.slice(-10).map(msg => ({
                role: msg.role === "bot" ? "assistant" : "user",
                content: msg.text
            }))


            const res = await fetchAPI<{ 
                success: boolean, 
                response: string, 
                type: string, 
                function_used: string,
                error?: string 
            }>("/mails/chatbot/conversation/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: input,
                    conversation_history: conversationHistory
                }),
            })

            const data = res;

            if (data.success && data.response) {
                const botMsg: ChatMessage = {
                    role: "bot",
                    text: data.response,
                    type: data.type || "conversation",
                    function_used: data.function_used,
                    timestamp: new Date()
                }
                setMessages(prev => [...prev, botMsg])
            } else {
                const errorMessage = data.error || "Je n'ai pas pu traiter votre message.";
                const botMsg: ChatMessage = {
                    role: "bot",
                    text: errorMessage,
                    type: "error",
                    timestamp: new Date()
                }
                setMessages(prev => [...prev, botMsg])
            }
        } catch (error) {
            console.error('Chat error:', error);
            const errorMsg: ChatMessage = {
                role: "bot",
                text: "Erreur lors de l'envoi. Veuillez réessayer.",
                type: "error",
                timestamp: new Date()
            }
            setMessages(prev => [...prev, errorMsg])
        } finally {
            setIsLoading(false)
        }
    }

    const formatMessage = (msg: ChatMessage) => {
        // Add visual indicators based on message type
        let className = `${styles.msg} ${msg.role === 'user' ? styles.user : styles.bot}`
        if (msg.type === 'email_summary') className += ` ${styles.emailSummary}`
        if (msg.type === 'email_reply') className += ` ${styles.emailReply}`
        if (msg.type === 'email_classification') className += ` ${styles.emailClassification}`
        if (msg.type === 'function_call') className += ` ${styles.functionCall}`
        if (msg.type === 'multi_step_completed') className += ` ${styles.multiStep}`
        if (msg.type === 'error') className += ` ${styles.error}`

        return (
            <div key={msg.timestamp?.getTime()} className={className}>
                <div className={styles.msgContent}>
                    {msg.role === 'bot' ? (
                        // Render bot messages with markdown support
                        <ReactMarkdown
                            components={{
                                // Custom styling for markdown elements
                                h1: ({children}) => <h1 className={styles.markdownH1}>{children}</h1>,
                                h2: ({children}) => <h2 className={styles.markdownH2}>{children}</h2>,
                                h3: ({children}) => <h3 className={styles.markdownH3}>{children}</h3>,
                                p: ({children}) => <p className={styles.markdownP}>{children}</p>,
                                strong: ({children}) => <strong className={styles.markdownStrong}>{children}</strong>,
                                code: ({children}) => <code className={styles.markdownCode}>{children}</code>,
                                pre: ({children}) => <pre className={styles.markdownPre}>{children}</pre>,
                                ul: ({children}) => <ul className={styles.markdownUl}>{children}</ul>,
                                ol: ({children}) => <ol className={styles.markdownOl}>{children}</ol>,
                                li: ({children}) => <li className={styles.markdownLi}>{children}</li>,
                                blockquote: ({children}) => <blockquote className={styles.markdownBlockquote}>{children}</blockquote>,
                                hr: () => <hr className={styles.markdownHr} />,
                            }}
                        >
                            {msg.text}
                        </ReactMarkdown>
                    ) : (
                        // Keep user messages as simple text
                        msg.text.split('\n').map((line, index) => (
                            <div key={index}>{line}</div>
                        ))
                    )}
                </div>
                {msg.function_used && (
                    <div className={styles.msgMeta}>
                        <small>🔧 Fonction utilisée: {msg.function_used}</small>
                    </div>
                )}
                <div className={styles.msgTimestamp}>
                    <small>{msg.timestamp?.toLocaleTimeString()}</small>
                </div>
            </div>
        )
    }

    return (
        <div className={styles.chatWindow}>
            <div className={styles.chatMessages}>
                {messages.map((msg) => formatMessage(msg))}
                {isLoading && (
                    <div className={`${styles.msg} ${styles.bot} ${styles.loading}`}>
                        <div className={styles.msgContent}>
                            <div>🤔 Je réfléchis...</div>
                        </div>
                    </div>
                )}
            </div>
            <div className={styles.chatInput}>
                <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && sendMessage()}
                    placeholder="Tapez votre message..."
                    disabled={isLoading}
                />
                <button onClick={sendMessage} disabled={isLoading || !input.trim()}>
                    {isLoading ? "..." : "Envoyer"}
                </button>
            </div>
        </div>
    )
}
