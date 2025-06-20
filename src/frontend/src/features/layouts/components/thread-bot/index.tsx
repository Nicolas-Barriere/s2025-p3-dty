import { ActionBar } from "./components/thread-action-bar"
import { ChatWindow } from "./components/chat-window"

export const ChatbotView = () => {
    return (
        <div className="thread-bot">
            <ActionBar />
            <h3>Hello</h3>
            <ChatWindow />
        </div>
    )
}
