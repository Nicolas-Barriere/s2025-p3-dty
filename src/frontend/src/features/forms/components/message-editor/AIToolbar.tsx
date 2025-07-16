import React, { useState, useEffect, useRef, useImperativeHandle, forwardRef } from "react";
import { useAIAnswer } from "./utils/ai";
import { BlockNoteEditor } from "@blocknote/core";


type AIToolbarProps = {
    threadId?: string;
    editor?: BlockNoteEditor<any, any, any>;
    getCurrentMessage?: () => Promise<string>; // Fonction pour récupérer le message actuel
    onRevert?: () => void;
    onKeep?: () => void;
    showActionButtons: boolean;
    onAIResponse?: (draft: string, prompt: string) => Promise<void>;
    isPending?: boolean;
    lastInstruction?: string;
};

const AIToolbar = forwardRef(({
    threadId,
    editor,
    getCurrentMessage,
    onRevert,
    onKeep,
    showActionButtons = false,
    onAIResponse,
    isPending = false,
    lastInstruction = ""
}: AIToolbarProps, ref) => {
    const [instruction, setInstruction] = useState(lastInstruction);
    const { requestAIAnswer } = useAIAnswer(threadId);
    const inputRef = useRef<HTMLInputElement>(null);
    const isInitialMount = useRef(true);

    useImperativeHandle(ref, () => ({
        focus: () => {
            inputRef.current?.focus();
        }
    }));

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    useEffect(() => {
        if (isInitialMount.current && lastInstruction) {
            setInstruction(lastInstruction);
            isInitialMount.current = false;
        }
        else if (!isInitialMount.current && lastInstruction) {
            setInstruction(lastInstruction);
        }
    }, [lastInstruction]);

    useEffect(() => {
        if (!showActionButtons) {
            if (lastInstruction) {
                setInstruction(lastInstruction);
            }
            setTimeout(() => {
                inputRef.current?.focus();
            }, 50);
        }
    }, [showActionButtons, lastInstruction]);

    useEffect(() => {
        // Ne créer l'écouteur que si les boutons d'action sont affichés
        if (showActionButtons && !isPending) {
            const handleActionKeys = (event: KeyboardEvent) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    onKeep && onKeep();
                } else if (event.key === 'Escape') {
                    event.preventDefault();
                    onRevert && onRevert();
                }
            };

            // Ajouter l'écouteur au document
            document.addEventListener('keydown', handleActionKeys);

            // Nettoyer l'écouteur lors du démontage ou quand showActionButtons devient false
            return () => {
                document.removeEventListener('keydown', handleActionKeys);
            };
        }
    }, [showActionButtons, isPending, onKeep, onRevert]);

    const handleSend = async () => {
        if (editor && !isPending) {
            let currentMessage = "";
            if (getCurrentMessage) {
                currentMessage = await getCurrentMessage();
            }
            const prompt = instruction;
            const draft = currentMessage ? currentMessage : "";
            if (onAIResponse) {
                await onAIResponse(draft, prompt);
            } else {
                await requestAIAnswer(draft, prompt, editor);
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