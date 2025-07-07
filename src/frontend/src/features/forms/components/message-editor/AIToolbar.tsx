import React, { useState } from "react";
import { useAIAnswer } from "./utils/ai";
import { BlockNoteEditor } from "@blocknote/core";


type AIToolbarProps = {
    threadId?: string;
    editor?: BlockNoteEditor;
    getCurrentMessage?: () => Promise<string>; // Fonction pour récupérer le message actuel
};

const AIToolbar = ({ threadId, editor, getCurrentMessage }: AIToolbarProps) => {
    const [instruction, setInstruction] = useState("");
    const { requestAIAnswer, isPending } = useAIAnswer(threadId);

    const handleSend = async () => {
        if (editor) {
            // Récupérer le contenu actuel du brouillon
            let currentMessage = "";
            if (getCurrentMessage) {
                currentMessage = await getCurrentMessage();
            }

            // Construire le contexte pour l'IA
            let context = `La demande est : ${instruction}`;

            // Ajouter le message brouillon au contexte s'il existe
            if (currentMessage) {
                context += `\n\nVoici le brouillon que l'utilisateur est en train de rédiger:\n${currentMessage}. Notamment essaye de partir de ce brouillon pour ta réponse`;
            }
            await requestAIAnswer(context, editor);
            setInstruction(""); // Clear input after sending
        }
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter' && !isPending && instruction.trim()) {
            event.preventDefault(); // Empêche le comportement par défaut
            handleSend();
        }
    };

    return (
        <div className="ai-toolbar-extension">
            <input
                type="text"
                value={instruction}
                onChange={e => setInstruction(e.target.value)}
                onKeyDown={handleKeyDown}
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