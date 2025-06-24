import { useState } from "react"
import styles from "./ChatWindow.module.css"
import { fetchAPI } from "@/features/api/fetch-api";
import { boolean } from "zod";

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


            const res = await fetchAPI<{ data: {success: boolean, response: string, type: string, function_used: string} }>("/mails/chatbot/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: input,
                    conversation_history: conversationHistory
                }),
            }
            )

            const data = res.data;

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
                const botMsg: ChatMessage = {
                    role: "bot",
                    text: "Désolé, je n'ai pas pu traiter votre message.",
                    type: "error",
                    timestamp: new Date()
                }
                setMessages(prev => [...prev, botMsg])
            }
        } catch (err) {
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
        if (msg.type === 'error') className += ` ${styles.error}`

        return (
            <div key={msg.timestamp?.getTime()} className={className}>
                <div className={styles.msgContent}>
                    {msg.text.split('\n').map((line, i) => (
                        <div key={i}>{line}</div>
                    ))}
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
                {messages.map((msg, i) => formatMessage(msg))}
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
