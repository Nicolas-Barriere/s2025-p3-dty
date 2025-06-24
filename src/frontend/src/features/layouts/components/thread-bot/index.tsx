import { ActionBar } from "./components/thread-action-bar"
import { ChatWindow } from "./components/chat-window"

export const ChatbotView = () => {
    return (
        <div className="thread-bot">
            <ActionBar />
            <ChatWindow />
        </div>
    )
}
