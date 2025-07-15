import { BasicTextStyleButton, BlockTypeSelect, CreateLinkButton, FormattingToolbar } from "@blocknote/react";
import React, { useState } from "react";

type MessageEditorToolbarProps = {
    onAIClick: () => void;
    active?: boolean;
};

const MessageEditorToolbar = ({ onAIClick, active = false }: MessageEditorToolbarProps) => {

    const [showTooltip, setShowTooltip] = useState(false);

    const handleAIClick = () => {
        onAIClick();
    }

    return (
        <FormattingToolbar>
            <BlockTypeSelect key={"blockTypeSelect"} />
            <BasicTextStyleButton
                basicTextStyle={"bold"}
                key={"boldStyleButton"}
            />
            <BasicTextStyleButton
                basicTextStyle={"italic"}
                key={"italicStyleButton"}
            />
            <BasicTextStyleButton
                basicTextStyle={"underline"}
                key={"underlineStyleButton"}
            />
            <BasicTextStyleButton
                basicTextStyle={"strike"}
                key={"strikeStyleButton"}
            />
            <BasicTextStyleButton
                key={"codeStyleButton"}
                basicTextStyle={"code"}
            />
            <CreateLinkButton key={"createLinkButton"} />

            <button
                type="button"
                onClick={handleAIClick}
                className={`ai-toolbar-btn ${active ? 'ai-active' : ''}`}
                title="Ouvrir la barre IA"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
            >
                <span className="material-icons">edit</span>
                {showTooltip && (
                    <div className="ai-toolbar-tooltip">
                        <div>
                            {active ? "Fermer l'assistant IA" : "Assistant IA"}
                        </div>
                        <div className="shortcut-hint">(⌘+Shift+L)</div>
                    </div>
                )}
            </button>
        </FormattingToolbar>
    )
}

export default MessageEditorToolbar;