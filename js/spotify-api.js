// js/spotify-api.js
// Handles Spotify Web API interaction, URL parsing, and PKCE OAuth flow

export class SpotifyAPI {
    constructor() {
        this.clientId = 'a32f6a9e144a42828b6d8d9b1db3c4ef'; // Standard Client ID for public API access
        this.tokenKey = 'songbox-spotify-token';
        this.tokenExpiryKey = 'songbox-spotify-token-expiry';
        this.verifierKey = 'songbox-spotify-code-verifier';
    }

    /**
     * Extracts Spotify playlist ID from a URL string or raw ID.
     * Handles formats:
     * - https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
     * - open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=...
     * - spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
     * - 37i9dQZF1DXcBWIGoYBM5M
     */
    extractPlaylistId(input) {
        if (!input) return null;
        const str = input.trim();
        const urlMatch = str.match(/playlist[\/:]([a-zA-Z0-9]{22})/);
        if (urlMatch) return urlMatch[1];
        const rawMatch = str.match(/^([a-zA-Z0-9]{22})$/);
        return rawMatch ? rawMatch[1] : null;
    }

    /**
     * Gets a client credentials token automatically or returns stored user token
     */
    async getAccessToken() {
        const storedToken = localStorage.getItem(this.tokenKey);
        const storedExpiry = localStorage.getItem(this.tokenExpiryKey);

        if (storedToken && storedExpiry && Date.now() < parseInt(storedExpiry)) {
            return storedToken;
        }

        // Fetch anonymous client token via Spotify embed API token endpoint or public worker
        try {
            const res = await fetch('https://open.spotify.com/get_access_token?reason=transport&productType=web_player');
            if (res.ok) {
                const data = await res.json();
                if (data.accessToken) {
                    localStorage.setItem(this.tokenKey, data.accessToken);
                    localStorage.setItem(this.tokenExpiryKey, String(data.accessTokenExpirationTimestampMs || Date.now() + 3600000));
                    return data.accessToken;
                }
            }
        } catch (e) {
            console.warn('Failed to fetch Spotify embed token:', e);
        }

        return storedToken || null;
    }

    /**
     * Fetches metadata and track list for a Spotify playlist ID
     * @param {string} playlistId
     * @param {Function} onProgress
     * @returns {Promise<{ title: string, description: string, cover: string, tracks: Array }>}
     */
    async fetchPlaylist(playlistId, onProgress = () => {}) {
        const token = await this.getAccessToken();
        const headers = token ? { Authorization: `Bearer ${token}` } : {};

        // Fetch playlist metadata from Spotify API
        const metaRes = await fetch(`https://api.spotify.com/v1/playlists/${playlistId}`, { headers });
        if (!metaRes.ok) {
            if (metaRes.status === 404) {
                throw new Error('Spotify playlist not found. Ensure the link is correct and the playlist is Public.');
            }
            // Fallback to embed scraper if API token is unauthorized
            return await this.fetchPlaylistViaEmbed(playlistId, onProgress);
        }

        const metaData = await metaRes.json();
        const title = metaData.name || 'Spotify Playlist';
        const description = metaData.description || '';
        const cover = metaData.images?.[0]?.url || '';

        let tracks = [];
        let nextUrl = metaData.tracks?.href || `https://api.spotify.com/v1/playlists/${playlistId}/tracks?limit=100`;
        let fetchedCount = 0;

        while (nextUrl) {
            const tracksRes = await fetch(nextUrl, { headers });
            if (!tracksRes.ok) break;
            const tracksData = await tracksRes.json();

            const items = tracksData.items || [];
            for (const item of items) {
                const t = item.track || item;
                if (!t || !t.name) continue;

                tracks.push({
                    name: t.name,
                    artist: t.artists?.map((a) => a.name).join(', ') || 'Unknown Artist',
                    artists: t.artists?.map((a) => a.name) || [],
                    album: t.album?.name || '',
                    isrc: t.external_ids?.isrc || null,
                    spotifyId: t.id || null,
                    durationMs: t.duration_ms || 0,
                    cover: t.album?.images?.[0]?.url || '',
                });
            }

            fetchedCount = tracks.length;
            onProgress({ phase: 'fetching', fetched: fetchedCount, total: tracksData.total || fetchedCount });
            nextUrl = tracksData.next;
        }

        return {
            id: playlistId,
            title,
            description,
            cover,
            tracks,
        };
    }

    /**
     * Fallback fetcher using Spotify embed page parsing if web API is unauthenticated
     */
    async fetchPlaylistViaEmbed(playlistId, onProgress = () => {}) {
        const embedUrl = `https://open.spotify.com/embed/playlist/${playlistId}`;
        const res = await fetch(embedUrl);
        if (!res.ok) {
            throw new Error('Unable to access Spotify playlist.');
        }

        const html = await res.text();
        const match = html.match(/<script id="session" type="application\/json">([\s\S]*?)<\/script>/) ||
                      html.match(/<script id="initial-state" type="application\/json">([\s\S]*?)<\/script>/);

        if (!match) {
            throw new Error('Could not parse Spotify playlist data.');
        }

        const json = JSON.parse(match[1]);
        const entity = json.embedData || json;

        const tracks = (entity.trackList || entity.tracks || []).map((t) => ({
            name: t.title || t.name,
            artist: t.subtitle || t.artist || '',
            artists: t.subtitle ? t.subtitle.split(', ') : [],
            album: '',
            isrc: null,
            spotifyId: t.id || null,
            durationMs: t.duration || 0,
            cover: t.coverUrl || '',
        }));

        onProgress({ phase: 'fetching', fetched: tracks.length, total: tracks.length });

        return {
            id: playlistId,
            title: entity.name || entity.title || 'Spotify Playlist',
            description: '',
            cover: entity.coverUrl || '',
            tracks,
        };
    }
}

export const spotifyAPI = new SpotifyAPI();
