import React, { useState, useEffect, useRef, useImperativeHandle, forwardRef } from "react";
import { useAIAnswer } from "./utils/ai";
import { BlockNoteEditor } from "@blocknote/core";


type AIToolbarProps = {
    threadId?: string;
    editor?: BlockNoteEditor<any, any, any>;
    getCurrentMessage?: () => Promise<string>; // Fonction pour récupérer le message actuel
    onRevert?: () => void;
    onKeep?: () => void;
    onRetry?: () => void;
    showActionButtons: boolean;
    onAIResponse?: (context: string) => Promise<void>;
    isPending?: boolean;
};

const AIToolbar = forwardRef(({
    threadId,
    editor,
    getCurrentMessage,
    onRevert,
    onKeep,
    onRetry,
    showActionButtons = false,
    onAIResponse,
    isPending = false
}: AIToolbarProps, ref) => {
    const [instruction, setInstruction] = useState("");
    const { requestAIAnswer } = useAIAnswer(threadId);
    const inputRef = useRef<HTMLInputElement>(null);

    useImperativeHandle(ref, () => ({
        focus: () => {
            inputRef.current?.focus();
        }
    }));

    // Focus automatique à l'apparition du composant
    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    const handleSend = async () => {
        if (editor && !isPending) {
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
            if (onAIResponse) {
                await onAIResponse(context);
            } else {
                await requestAIAnswer(context, editor);
            }
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
            {showActionButtons ? (
                <div className="ai-action-buttons">
                    <div className="ai-action-controls">
                        <button
                            type="button"
                            className="revert confirm-button"
                            onClick={onRevert}
                            title="Annuler les modifications"
                            disabled={isPending}
                        >
                            <span className="material-icons">undo</span>
                            <span>Annuler</span>
                        </button>
                        <button
                            type="button"
                            className="keep confirm-button"
                            onClick={onKeep}
                            title="Conserver les modifications"
                            disabled={isPending}
                        >
                            <span className="material-icons">check</span>
                            <span>Accepter</span>
                        </button>
                    </div>
                </div>
            ) : (
                <>
                    <input
                        ref={inputRef}
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
                            <span className="material-icons">check</span>
                        )}
                    </button>
                </>
            )}
        </div>
    );
});

AIToolbar.displayName = 'AIToolbar';

export default AIToolbar;