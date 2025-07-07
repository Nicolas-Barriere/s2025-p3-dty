import { BasicTextStyleButton, BlockTypeSelect, CreateLinkButton, FormattingToolbar } from "@blocknote/react";
import { AIButton } from './AIButton';
import React, { useState } from "react";

type MessageEditorToolbarProps = {
    onAIClick: () => void;
};

const MessageEditorToolbar = ({ onAIClick }: MessageEditorToolbarProps) => {
    const [showAIInput, setShowAIInput] = useState(false);
    const [aiPrompt, setAIPrompt] = useState("");
    const [showTooltip, setShowTooltip] = useState(false);

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
                onClick={onAIClick}
                className="ai-toolbar-btn"
                title="Ouvrir la barre IA"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
            >
                <span class="material-icons">auto_awesome</span>
                {showTooltip && (
                    <div className="ai-toolbar-tooltip">
                        Actions IA
                    </div>
                )}
            </button>
        </FormattingToolbar>
    )
}

export default MessageEditorToolbar;
