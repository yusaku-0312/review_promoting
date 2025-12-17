async function copyToClipboard() {
    const textarea = document.getElementById('message_area');

    // Success handling helper
    const handleSuccess = () => {
        const successMsg = document.getElementById('copy_success');
        successMsg.classList.remove('hidden');
        successMsg.classList.add('animate-fade-in');

        setTimeout(() => {
            successMsg.classList.add('hidden');
        }, 2000);
    };

    // Error handling helper
    const handleError = (err) => {
        console.error('Copy failed: ', err);
        alert('クリップボードへのコピーに失敗しました。手動でコピーしてください。');
    };

    // Modern API
    if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
            await navigator.clipboard.writeText(textarea.value);
            handleSuccess();
        } catch (err) {
            // If secure context requirement fails, try fallback
            fallbackCopyTextToClipboard(textarea.value);
        }
    } else {
        // Fallback for older browsers or non-secure contexts
        fallbackCopyTextToClipboard(textarea.value);
    }

    function fallbackCopyTextToClipboard(text) {
        try {
            textarea.select();
            textarea.setSelectionRange(0, 99999); // For mobile devices

            const successful = document.execCommand('copy');
            if (successful) {
                handleSuccess();
                // Deselect to avoid visual clutter
                window.getSelection().removeAllRanges();
            } else {
                throw new Error('execCommand failed');
            }
        } catch (err) {
            handleError(err);
        }
    }
}

async function updateShopUrl(shopId) {
    if (!shopId) return;

    try {
        const response = await fetch('/update_shop_url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ shop_id: shopId }),
        });

        const data = await response.json();

        if (data.success) {
            const textarea = document.getElementById('message_area');
            let currentText = textarea.value;

            // Regex to find the URL part (rough match based on template format)
            // Template: こちらのURLから口コミも書いていただけると嬉しいです！（URL）
            // We look for the pattern inside parentheses after the specific text
            // Note: This relies on the specific text structure.

            const urlPattern = /(こちらのURLから口コミも書いていただけると嬉しいです！\（)(.*?)(\）)/;

            if (currentText.match(urlPattern)) {
                const newText = currentText.replace(urlPattern, `$1${data.url}$3`);
                textarea.value = newText;
            } else {
                // If pattern not found (e.g. user edited it away), we might append or alert.
                // For MVP, if they edited it, we might just leave it or try to append.
                // Let's try to append if missing, or just ignore to be safe not to break user edits.
                console.log("URL pattern not found, skipping auto-update");
            }

        } else {
            console.error('Failed to update shop URL');
        }
    } catch (error) {
        console.error('Error updating shop URL:', error);
    }
}
