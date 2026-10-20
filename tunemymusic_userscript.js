// ==UserScript==
// @name         TuneMyMusic Bulk Auto-Importer for Spotify
// @namespace    https://open.spotify.com/
// @version      1.0
// @description  Automates multiple CSV batch uploads to TuneMyMusic without manual clicking
// @match        https://www.tunemymusic.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Floating UI Panel
    const panel = document.createElement('div');
    panel.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 999999;
        background: #181818;
        border: 2px solid #1DB954;
        border-radius: 12px;
        padding: 16px;
        color: white;
        font-family: sans-serif;
        box-shadow: 0 8px 32px rgba(0,0,0,0.8);
        max-width: 320px;
    `;

    panel.innerHTML = `
        <h4 style="margin: 0 0 8px 0; color: #1DB954; font-size: 15px;">🎵 Bulk CSV Queue Importer</h4>
        <p style="font-size: 12px; color: #b3b3b3; margin: 0 0 10px 0;">Select your chunked CSV files to auto-upload sequentially:</p>
        <input type="file" id="tmm-csv-batch-input" multiple accept=".csv" style="font-size: 11px; margin-bottom: 10px; width: 100%; color: #ddd;" />
        <div id="tmm-status" style="font-size: 12px; color: #1DB954; font-weight: bold; margin-bottom: 8px;">Waiting for files...</div>
        <button id="tmm-start-btn" style="background: #1DB954; color: black; font-weight: bold; border: none; border-radius: 20px; padding: 8px 16px; width: 100%; cursor: pointer;">Start Auto-Transfer</button>
    `;

    document.body.appendChild(panel);

    let fileQueue = [];
    let currentIndex = 0;

    const fileInput = document.getElementById('tmm-csv-batch-input');
    const statusText = document.getElementById('tmm-status');
    const startBtn = document.getElementById('tmm-start-btn');

    fileInput.addEventListener('change', (e) => {
        fileQueue = Array.from(e.target.files);
        statusText.innerText = `${fileQueue.length} files selected in queue.`;
    });

    startBtn.addEventListener('click', () => {
        if (!fileQueue.length) {
            alert('Please select one or more CSV files from playlists/spotify_exports/csv/ first!');
            return;
        }
        statusText.innerText = `Starting transfer (1/${fileQueue.length})...`;
        startBtn.disabled = true;
        processNextFile();
    });

    function processNextFile() {
        if (currentIndex >= fileQueue.length) {
            statusText.innerText = '🎉 All queued files transferred!';
            startBtn.disabled = false;
            return;
        }

        const file = fileQueue[currentIndex];
        statusText.innerText = `[${currentIndex + 1}/${fileQueue.length}] Uploading ${file.name}...`;

        // 1. If not on transfer page, go to it
        if (!window.location.pathname.includes('/transfer')) {
            window.location.href = '/transfer';
            return;
        }

        // 2. Automate steps on page
        setTimeout(() => {
            // Find and click "Upload file"
            const uploadBtn = Array.from(document.querySelectorAll('*')).find(el => el.textContent.trim() === 'Upload file' && el.offsetParent !== null);
            if (uploadBtn) uploadBtn.click();

            setTimeout(() => {
                // Find input type=file
                const fileInputs = document.querySelectorAll('input[type="file"]');
                const targetInput = fileInputs[fileInputs.length - 1];
                if (targetInput) {
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    targetInput.files = dataTransfer.files;
                    targetInput.dispatchEvent(new Event('change', { bubbles: true }));

                    // Wait for mapping / Continue screen
                    setTimeout(() => {
                        const continueBtn = Array.from(document.querySelectorAll('button, span, div')).find(el => el.textContent.trim() === 'Continue');
                        if (continueBtn) continueBtn.click();

                        // Wait for Destination screen
                        setTimeout(() => {
                            const spotifyBtn = Array.from(document.querySelectorAll('*')).find(el => el.textContent.trim() === 'Spotify');
                            if (spotifyBtn) spotifyBtn.click();

                            // Wait for Start Transfer screen
                            setTimeout(() => {
                                const startTransfer = Array.from(document.querySelectorAll('*')).find(el => el.textContent.trim() === 'Start Transfer');
                                if (startTransfer) {
                                    startTransfer.click();
                                    statusText.innerText = `[${currentIndex + 1}/${fileQueue.length}] Transferring...`;

                                    // Poll for completion
                                    const interval = setInterval(() => {
                                        const bodyText = document.body.innerText;
                                        if (bodyText.includes('Transfer completed') || bodyText.includes('Transfer Completed')) {
                                            clearInterval(interval);
                                            currentIndex++;
                                            setTimeout(() => {
                                                window.location.href = '/transfer';
                                                setTimeout(processNextFile, 3000);
                                            }, 2000);
                                        }
                                    }, 3000);
                                }
                            }, 3000);
                        }, 2500);
                    }, 2500);
                }
            }, 1500);
        }, 1000);
    }
})();
