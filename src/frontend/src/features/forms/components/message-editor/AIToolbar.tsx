import React, { useState, useEffect, useRef, useImperativeHandle, forwardRef } from "react";
import { useAIAnswer } from "./utils/ai";
import { BlockNoteEditor } from "@blocknote/core";
import { Spinner } from "@gouvfr-lasuite/ui-kit";
import TextareaAutosize from 'react-textarea-autosize';
import { useTranslation } from "react-i18next";

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
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const isInitialMount = useRef(true);
    const { t } = useTranslation();

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

            document.addEventListener('keydown', handleActionKeys);

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
            setInstruction("");
        }
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === 'Enter' && !event.shiftKey && !isPending && instruction.trim()) {
            event.preventDefault();
            handleSend();
        }
        if (event.key === 'Enter' && event.shiftKey) {
            event.preventDefault();
            const textarea = event.target as HTMLTextAreaElement;
            const { selectionStart, selectionEnd, value } = textarea;
            const newValue = value.slice(0, selectionStart) + "\n" + value.slice(selectionEnd);
            setInstruction(newValue);
            setTimeout(() => {
                textarea.selectionStart = textarea.selectionEnd = selectionStart + 1;
            }, 0);
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
                            <span>{t("aiToolbar.Cancel")}</span>
                        </button>
                        <button
                            type="button"
                            className="keep confirm-button"
                            onClick={onKeep}
                            title="Conserver les modifications"
                            disabled={isPending}
                        >
                            <span className="material-icons">check</span>
                            <span>{t("aiToolbar.Accept")}</span>
                        </button>
                    </div>
                </div>
            ) : (
                <>
                    <TextareaAutosize
                        ref={inputRef}
                        value={instruction}
                        onChange={e => setInstruction(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={t("aiToolbar.placeholder")}
                        className="ai-toolbar-input"
                        disabled={isPending}
                        minRows={1}
                        maxRows={10}
                    />
                    <button
                        type="button"
                        className="ai-toolbar-send"
                        onClick={handleSend}
                        disabled={isPending || !instruction.trim()}
                    >
                        {isPending ? (
                            <Spinner />
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