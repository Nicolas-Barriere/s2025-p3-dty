import { useState } from "react"
import { useChatbotApiAnswerCreate } from "@/features/api/gen/chatbot/chatbot";

export const ChatWindow = () => {
    type ChatMessage = { role: "user" | "bot"; text: string }
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [input, setInput] = useState("")

    const { mutate: sendToChatbot, isPending } = useChatbotApiAnswerCreate({
        mutation: {
            onSuccess: (response) => {
                console.log("Structure de la réponse:", response.data);
                console.log("Contenu response:", response.data.response);

                // Traite la réponse du chatbot
                const botMsg: ChatMessage = {
                    role: "bot",
                    text: (response.data.response as any)?.response || "Réponse reçue"
                }
                setMessages(prev => [...prev, botMsg])
            },
            onError: (error) => {
                const botMsg: ChatMessage = {
                    role: "bot",
                    text: "Erreur lors de l'envoi"
                }
                setMessages(prev => [...prev, botMsg])
            }
        }
    })

    const sendMessage = async () => {
        if (!input.trim()) return

        const userMsg: ChatMessage = { role: "user", text: input }
        setMessages(prev => [...prev, userMsg])

        sendToChatbot({
            data: {
                original_mail: input,  // Adapte selon l'API backend
                context: "",
                tone: "professional",
                language: "french",
                operation: "answer",
            }
        })

        setInput("")
    }

    return (
        <div className="chat-window">
            <div className="chat-messages">
                {messages.map((msg, i) => (
                    <div key={i} className={`msg ${msg.role}`}>
                        {msg.text}
                    </div>
                ))}
            </div>
            <div className="chat-input">
                <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && sendMessage()}
                    disabled={isPending}
                    placeholder="Tapez votre message..."
                />
                <button onClick={sendMessage}>{isPending ? "Envoi..." : "Envoyer"}</button>
            </div>
        </div>
    )
}
