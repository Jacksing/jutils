import os
import requests

BASE_PATH = "E:\MD\Kingeki"
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

url = 'http://i.imanhua88.com/imgb/J/%BD%F8%BB%F7%B5%C4%BE%DE%C8%CB/%B5%DA{section}%BB%B0/{page}.jpg'
url = 'http://hicomic.bbhou.com/comic/2/713/{section}/{page}.jpg'

# http://hicomic.bbhou.com/comic/2/713/33601/0002.jpg
# http://hicomic.bbhou.com/comic/2/713/33602/0000.jpg
# http://hicomic.bbhou.com/comic/2/713/33602/0002.jpg
# http://hicomic.bbhou.com/comic/2/713/142889/0000.jpg
# http://hicomic.bbhou.com/comic/2/713/151980/0000.jpg

def downloadImageFile(imgUrl, work_path):
    local_filename = imgUrl.split('/')[-1]
    print("Download Image File=", local_filename)
    r = requests.get(imgUrl, stream=True, headers=headers) # here we need to set stream = True parameter
    if r.status_code != 200:
        return None
    with open(os.path.join(work_path, local_filename), 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
        f.close()
    return local_filename

def downloadSection(section_id):
    work_path = os.path.join(BASE_PATH, str(section_id))
    try:
        os.makedirs(work_path)
    except:
        pass
    url_list = [url.format(section=section_id, page=str(i).zfill(4)) for i in range(1, 201)]

    for u in url_list:
        if not downloadImageFile(u, work_path):
            break

if __name__ == '__main__':
    section_list = range(33601, 33656)

    # for section_id in section_list:
    for section_id in [33601, 33611]:
        downloadSection(section_id)
