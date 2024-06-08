import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from tqdm import tqdm

logging.basicConfig(filename='download.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def download_catalog(url=None) -> str:

    logging.info(f"Téléchargement du catalogue de l'anime {url}")
    eps = []
    urls = []

    try:

        response = requests.get(url + 'episodes.js').text
        pattern = r"var eps.[0-9]+= \[.*?\];"
        for ep in re.findall(pattern, response, re.DOTALL):
            pattern = r"var eps(.[0-9]+)"
            ep_number = re.search(pattern, ep).group(1)
            pattern = r"\[(.*?)\];"
            matches = re.findall(pattern, ep, re.DOTALL)[0].split(',')
            for url in matches:
                url = url.replace('\'', '')
                url = url.replace('\n', '')
                url = url.replace(',', '')
                if url != '':
                    urls.append(url)

            eps.append({
                'ep': ep_number,
                'urls': urls
            })
            urls = []
        logging.info("Catalogue : %s", json.dumps(eps))
    except Exception as e:
        print(f"Erreur lors du téléchargement du catalogue : {e}")
        logging.error("Erreur lors du téléchargement du catalogue : %s", e)

    return eps


def download_file(url, destination):

    try:
        # Envoie une requête HTTP HEAD pour obtenir la taille du fichier
        response = requests.head(url)
        total_size = int(response.headers.get('content-length', 0))

        # Télécharge le fichier avec une barre de progression
        with requests.get(url, stream=True) as response, open(destination, 'wb') as file, tqdm(
            desc=destination,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
                bar.update(len(chunk))
    except Exception as e:
        print(f"Erreur lors du téléchargement du fichier : {e}")
        logging.error("Erreur lors du téléchargement du fichier : %s", e)


def download_in_batches(files_to_download, batch_size=5):
    total_files = len(files_to_download)
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        for i in range(0, total_files, batch_size):
            batch = files_to_download[i:i+batch_size]
            futures = [executor.submit(download_file, url, filename)
                       for url, filename in batch]
            for future in tqdm(as_completed(futures), total=len(batch), desc=f"Batch {i//batch_size + 1}"):
                try:
                    future.result()
                except Exception as e:
                    print(f"Erreur lors du téléchargement : {e}")
                    logging.error("Erreur lors du téléchargement : %s", e)


if __name__ == '__main__':
    url = input("Veuillez entrer l'URL du fichier à télécharger : ").strip()
    anime = url.replace(
        'https://anime-sama.fr/catalogue/', '').replace("/scan/vf/", '')
    Path(anime).mkdir(parents=True, exist_ok=True)

    catalog = download_catalog(url)

    for ep in catalog:
        output_dir = Path(f"{anime}/{ep['ep']}")
        output_dir.mkdir(parents=True, exist_ok=True)
        # Préparer la liste des fichiers à télécharger
        files_to_download = [
            (url, str(output_dir / f"{index}.jpg")) for index, url in enumerate(ep['urls'])]
        # Lancer le téléchargement
        download_in_batches(files_to_download, batch_size=5)
