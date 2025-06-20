import { useState } from "react"

export const ChatWindow = () => {
    type ChatMessage = { role: "user" | "bot"; text: string }
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [input, setInput] = useState("")

    const sendMessage = async () => {
        if (!input.trim()) return

        const userMsg: ChatMessage = { role: "user", text: input }
        setMessages(prev => [...prev, userMsg])
        setInput("")

        try {
            const res = await fetch("http://localhost:8071/mails/chatbot/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: input }),
            })

            const data = await res.json()
            
            if (data.success && data.response) {
                const botMsg: ChatMessage = { role: "bot", text: data.response }
                setMessages(prev => [...prev, botMsg])
            } else {
                const botMsg: ChatMessage = { role: "bot", text: "Désolé, je n'ai pas pu traiter votre message." }
                setMessages(prev => [...prev, botMsg])
            }
        } catch (err) {
            setMessages(prev => [...prev, { role: "bot", text: "Erreur lors de l'envoi" }])
        }
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
                />
                <button onClick={sendMessage}>Envoyer</button>
            </div>
        </div>
    )
}
