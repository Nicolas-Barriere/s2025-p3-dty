import React, { useState } from "react";
import { useAIAnswer } from "./utils/ai";
import { BlockNoteEditor } from "@blocknote/core";


type AIToolbarProps = {
    threadId?: string;
    editor?: BlockNoteEditor;
};

const AIToolbar = ({ threadId, editor }: AIToolbarProps) => {
    const [instruction, setInstruction] = useState("");
    const { requestAIAnswer, isPending } = useAIAnswer(threadId);

    const handleSend = async () => {
        if (editor) {
            await requestAIAnswer(instruction, editor);
            setInstruction(""); // Clear input after sending
        }
    };
    return (
        <div className="ai-toolbar-extension">
            <input
                type="text"
                value={instruction}
                onChange={e => setInstruction(e.target.value)}
                placeholder="Consigne IA…"
                className="ai-toolbar-input"
                disabled={isPending}
            />
            <button
                type="button"
                className="ai-toolbar-send"
                onClick={handleSend}
                disabled={isPending || !instruction.trim()}
            >
                {isPending ? (
                    <span className="material-icons">hourglass_empty</span>
                ) : (
                    <span className="material-icons">send</span>
                )}
            </button>
        </div>
    );
};

export default AIToolbar;