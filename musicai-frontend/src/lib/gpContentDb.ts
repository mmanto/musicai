/**
 * IndexedDB store for GP file binary content.
 * localStorage has a ~5MB cap; GP files exceed it so we keep them here.
 * Keys are the MusicFile.id values that zustand already persists.
 */
const DB_NAME = 'musicai-gp-content'
const STORE = 'content'
const VERSION = 1

let _db: Promise<IDBDatabase> | null = null

function getDb(): Promise<IDBDatabase> {
  if (!_db) {
    _db = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, VERSION)
      req.onupgradeneeded = () => req.result.createObjectStore(STORE)
      req.onsuccess = () => resolve(req.result)
      req.onerror = () => { _db = null; reject(req.error) }
    })
  }
  return _db
}

export async function saveGpContent(fileId: string, buffer: ArrayBuffer): Promise<void> {
  const db = await getDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).put(buffer, fileId)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function loadGpContent(fileId: string): Promise<ArrayBuffer | null> {
  const db = await getDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly')
    const req = tx.objectStore(STORE).get(fileId)
    req.onsuccess = () => resolve((req.result as ArrayBuffer | undefined) ?? null)
    req.onerror = () => reject(req.error)
  })
}

export async function deleteGpContent(fileId: string): Promise<void> {
  const db = await getDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).delete(fileId)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}
