(function (root) {
  'use strict';
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function safeUrl(value) {
    if (typeof value !== 'string' || /[\s"'<>`\\]/.test(value)) return false;
    try { return ['https:', 'http:'].includes(new URL(value).protocol); } catch { return false; }
  }
  function imageUrl(value, fallback) { return safeUrl(value) ? value : fallback; }
  function score(anime) {
    const value = anime?.averageScore;
    return typeof value === 'number' && Number.isFinite(value) && value > 0 && value <= 100 ? value : null;
  }
  function release(item) {
    if (!item || typeof item.slug !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(item.slug)) return null;
    const number = (value, maximum=1000000) => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= maximum ? value : null;
    return {...item,
      title:Object.fromEntries(Object.entries(item.title || {}).filter(([,value]) => typeof value === 'string')),
      genres:Array.isArray(item.genres) ? item.genres.filter(value => typeof value === 'string') : [],
      format:['TV','TV_SHORT','MOVIE','SPECIAL','OVA','ONA','MUSIC'].includes(item.format) ? item.format : null,
      seasonYear:number(item.seasonYear,2200), duration:number(item.duration,10000),
      available_episodes_count:number(item.available_episodes_count ?? item.translated_episodes_count) ?? 0,
      translated_episodes_count:number(item.translated_episodes_count) ?? 0,
      popularity:number(item.popularity,1000000000), averageScore:score(item),
      coverImage:imageUrl(item.coverImage,''), bannerImage:imageUrl(item.bannerImage,''),
      description:typeof item.description === 'string' ? item.description : '',
      studio:typeof item.studio === 'string' ? item.studio : '',
      color:typeof item.color === 'string' && /^#[a-f0-9]{6}$/i.test(item.color) ? item.color : null
    };
  }
  function episodes(anime) {
    if (!Array.isArray(anime?.subtitles)) return [];
    return anime.subtitles.filter(row => Number.isInteger(row.episode) && row.episode >= 0).map(row => ({
      episode: row.episode,
      files: Object.fromEntries(['srt','vtt','ass'].filter(ext => safeUrl(row.files?.[ext])).map(ext => [ext,row.files[ext]])),
      assets: row.assets || {}
    }));
  }
  function readLanguage() {
    try { const lang = localStorage.getItem('ask_lang'); return ['kk','en','ja'].includes(lang) ? lang : 'kk'; } catch { return 'kk'; }
  }
  function saveLanguage(lang) { try { localStorage.setItem('ask_lang',lang); } catch {} }
  const api = {escapeHtml, imageUrl, score, release, episodes, readLanguage, saveLanguage};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CatalogRuntime = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
