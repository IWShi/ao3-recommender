#AO3 Recommendations - Iris Shi - July 2022

from bs4 import BeautifulSoup
from urllib.request import *
from urllib.parse import *

DOMAIN = "https://archiveofourown.org"
VIEW_ADULT = "?view_adult=True"     #allows urlopen to open links to Mature/Explicit works
TAG_IDS = {
    "rating": {},
    "archive_warning": {},
    "category": {},
    "fandom": {},
    "relationship": {},
    "character": {},
    "freeform": {}
}
TAG_NAMES = {}      #maps URLs to official tag names
TAG_COUNT = {}      #maps official tag names to the number of works containing that tag
QUERY = [
    ('commit', 'Sort and Filter')
]
PUNCTUATION = {",", ".", "?", "!", "'", "\""}

def get_soup(url):
    """
    Given a URL, returns a BeautifulSoup object representing the HTML of the webpage associated with the URL
    """
    with urlopen(url) as response:
        soup = BeautifulSoup(response, "html.parser")
    
    return soup


def get_tag_id(soup, tag_name, tag_type):
    """
    Given a BeautifulSoup object representing a webpage associated with a particular tag, adds the ID of that
    tag to the TAG_IDS dictionary
    """
    for tag in soup.find(id="include_" + tag_type + "_tags").find_all("label"):
        if tag_name == " ".join(tag.get_text().strip().split(" ")[:-1]):
            TAG_IDS[tag_type][tag_name] = tag["for"].split("_")[-1]
            break


def get_link_info(link, investigate=False, tag_type=None):
    """
    Given an 'a' HTML tag, returns a list with two elements: (1) the name associated with the hyperlink and 
    (2) the URL itself. 
    * If investigate=True, the name associated with the hyperlink will be found by opening the URL and 
    looking at the title text of the webpage
    * If investigate=False, the name associated with the hyperlink will just be the string inside the HTML tag
    """
    url = DOMAIN + link["href"]
    if investigate:
        if url not in TAG_NAMES:
            soup = get_soup(url)
            header = soup.find(id="main").h2
            
            if header.a:    #indicates a tag that can be filtered on
                tag_name = header.a.string.strip()
                TAG_NAMES[url] = tag_name
                TAG_COUNT[tag_name] = get_number_of_works(soup)
                get_tag_id(soup, tag_name, tag_type)
            else:           #indicates a tag that cannot be filtered on
                tag_name = header.string.strip()
                TAG_NAMES[url] = tag_name
                TAG_COUNT[tag_name] = -1    #tags that cannot be filtered on have no official count
        
        return [TAG_NAMES[url], url]
    else:
        return [link.string, url]


def get_user_info(url):
    """
    Given a url to a user's AO3 page, returns a list with two elements: (1) the pseud of the user and (2) 
    the user's actual ID name
    """
    split_url = url.split("/")
    return [split_url[-1], split_url[-3]]   #[pseud, user ID]


def prettify_url(url):
    """
    Given a work URL, processes it so that it's in the correct form to be stored in the metadata about a work 
    """
    if "chapters" in url:   #removes the /chapters/ portion of the URL
        url = "/".join(url.split("/")[:-2]) 
        url += VIEW_ADULT
    
    return url


def get_work_id(url):
    """
    Given a URL to a work on AO3, returns the work ID
    """
    split_url = url.split("/")
    id = ""
    for char in split_url[split_url.index("works") + 1]:
        if char.isdigit():
            id += char
    
    return id


def get_number_of_works(soup, user_page=False):
    """
    Given a BeautifulSoup object representing a listing of works on AO3, returns the total number of works
    in the listing 

    user_page=True indicates that this is a listing on a user's page (i.e. formatted slightly differently)
    """
    split_header = soup.find(id="main").h2.get_text().strip().split(" ")
    if user_page:
        num_works = int(split_header[split_header.index("by") - 2])
    else:
        num_works = int(split_header[split_header.index("in") - 2])
    
    return num_works


def filter_bookmarks(work_data, used_ids, tag_type, query, min_bookmark_count=0):
    """
    Given a query that already contains information about a user, searches the bookmarks of that user for a work
    to recommend by filtering for a specific kind of tag (fandom, relationship, etc.)

    min_bookmark_count is the minimum number of total bookmarks that the filtered search must give in order to 
    proceed with the recommendation procedure (e.g. for min_bookmark_count=0, can't rec anything if the user 
    has bookmarked 0 works matching the filters)
    """
    for tag in work_data[tag_type]:
        query.append(('include_bookmark_search[' + tag_type + '_ids][]', TAG_IDS[tag_type][tag]))
        tag_page = get_soup(DOMAIN + "/bookmarks?" + urlencode(query))

        if get_number_of_works(tag_page, user_page=True) > min_bookmark_count:
            used_ids |= get_new_work(tag_page, used_ids, class_name="bookmark index group")
        
        query.pop()
    
    return used_ids


def get_work_data(url):
    """
    Given a URL for a work on AO3, returns a dictionary containing metadata about the work, including:
        * URL
        * work ID
        * title
        * author (including URL to author's dashboard and info about pseuds)
        * tags (rating, warnings, category, fandom, relationships, characters, freeform tags)
    """
    if VIEW_ADULT not in url:
        url += VIEW_ADULT
    soup = get_soup(url)

    data = {
        "url": prettify_url(url),
        "id": get_work_id(url),
        "title": soup.find(class_="title heading").string.strip()
    }

    data["author"] = []
    for author in soup.find(class_="byline heading").contents:
        try:
            author_info = get_link_info(author)
            author_info += get_user_info(author_info[1])     #[byline, URL, pseud ID, user ID]
            if author_info[3] == "orphan_account":
                data["author"].append([])
            else:
                data["author"].append(author_info)
        except TypeError:  #if get_link_info throws an error because the author is anonymous and doesn't have a link
            if author.strip() == "Anonymous": 
                data["author"].append([])

    tags = soup.find(class_="work meta group").find_all("dd")   #includes metadata such as fandom, language, rating, etc.
    for tag in tags:   
        tag_type = tag["class"][0]  #the kind of tag (i.e. fandom, language, rating, etc.)
        
        if tag_type == "language":     #don't need any more info once we reach stats/collections
            break
        elif tag_type == "warning":
            tag_type = "archive_warning"
        
        if tag.a:   #some types of tags have links, some don't
            data[tag_type] = []
            for link in tag.find_all("a"):  #some types of tags cover multiple tags
                data[tag_type].append(get_link_info(link, investigate=True, tag_type=tag_type)[0])
        else:
            data[tag_type] = tag.string.strip()
    
    return data


def print_work(data):
    """
    Given a dictionary of metadata about a work, prints the pertinent information in a readable manner
    """
    print("URL:\t\t", data["url"])
    print("TITLE:\t\t", data["title"])
    print("AUTHOR(S):\t", ", ".join(data["author"]))
    print("FANDOM(S):\t", ", ".join(data["fandom"]))
    print("SUMMARY:\n" + data["summary"])
    print("\n")


def get_new_work(soup, used_ids, class_name="work index group"):
    """
    Given a BeautifulSoup object representing a webpage with a list of works on AO3, prints the first work
    on the page that hasn't already been seen and adds that work's ID to the set of used/seen IDs

    If the given webpage represents a list of bookmarked works, class_name should be set to 'bookmark index group'
    instead
    """ 
    recced = False      #keeps track of whether any work has been recced yet
    while not recced:    
        new_works = soup.find(id="main").find(class_=class_name)

        for new_work in new_works.find_all(role="article"):
            new_work_link = new_work.find(class_="header module").a
            if "series" in new_work_link["href"]:     #if the new work represents a series of works, rec the first work in the series
                new_work = get_soup(DOMAIN + new_work_link["href"]).find(class_="series work index group").find(role="article")
            new_id = get_work_id(get_link_info(new_work.find(class_="header module").a)[1])      #gets the ID of each new work
            
            if new_id not in used_ids:     #if this new work hasn't been seen before
                used_ids.add(new_id)
                
                new_work_data = {   #don't need all of the work data, only some of it
                    "url": DOMAIN + "/works/" + new_id,
                    "title": new_work.find(class_="header module").a.string,
                    "author": [author.string for author in new_work.find(class_="header module").find_all(rel="author")],
                    "fandom": [fandom.string for fandom in new_work.find(class_="fandoms heading").find_all("a")]
                }

                if not new_work_data["author"]:     #if new_work possesses no tags with attribute rel="author"
                    new_work_data["author"] = ["Anonymous"]
                
                try:
                    summary = []
                    for text in new_work.find(class_="userstuff summary").stripped_strings:
                        if summary and text[0] not in PUNCTUATION:  #if this isn't the first text string
                            text = " " + text
                        summary.append(text)
                    new_work_data["summary"] = "".join(summary)
                except AttributeError:  #if the work doesn't hvae a summary
                    new_work_data["summary"] = "\t N/A"
                
                print_work(new_work_data)
                recced = True
                break
        
        if not recced:  #if no works have been recc'ed on this page, try the next page
            try:
                next_page_link = get_link_info(soup.find(role="navigation", title="pagination").find(class_="next").a)[1]
                soup = get_soup(next_page_link)
            except (TypeError, AttributeError):  #if no new works have been recc'ed, but no new works CAN be recc'ed
                break

    return used_ids


def get_author_works(work_data, used_ids):
    """
    Given information about a work on AO3, prints a list of similar works that by the same author(s) and returns 
    a set containing the IDs of all the works recc'ed thus far
    """  
    for author in work_data["author"]:
        if not author:  #if author is an empty list (i.e. the author is anonymous/orphan_account)
            continue

        query = QUERY.copy()
        query.append(('work_search[sort_column]', 'kudos_count'))
        query.append(('pseud_id', author[2]))
        query.append(('user_id', author[3]))
        
        for fandom in work_data["fandom"]:
            recced = False   #for each fandom, goal is to rec 1 other fic by the same author(s) in that same fandom (ideally with the same relationships, but possibly not)
            query.append(('fandom_id', TAG_IDS["fandom"][fandom]))
            fandom_page = get_soup(DOMAIN + "/works?" + urlencode(query))   #go to webpage containing all works by the author in a particular fandom
            
            if len(author) != 5:
                bookmark_link = "/users/" + author[3] + "/pseuds/" + author[2] + "/bookmarks"
                bookmark_count = int(fandom_page.find(id="dashboard").find(href=bookmark_link).string.split(" ")[-1][1:-1])
                if bookmark_count > 0:  #if the author has at least 1 work bookmarked
                    author.append(True)
                else:   #if the author has 0 works bookmarked
                    author.append(False)

            if get_number_of_works(fandom_page, user_page=True) > 1:  #if the author has more than one work in this fandom
                if "relationship" in work_data:
                    for ship in work_data["relationship"]:
                        query.append(('include_work_search[relationship_ids][]', TAG_IDS["relationship"][ship]))
                        ship_page = get_soup(DOMAIN + "/works?" + urlencode(query))
                        if get_number_of_works(ship_page, user_page=True) > 1:  #if author has at least one other work with this relationship
                            recced = True
                            used_ids |= get_new_work(ship_page, used_ids)
                        query.pop()     #remove the relationship part of the query
                
                if not recced:      #if the author has no other works with the same relationship, rec one of the author's works from the same fandom
                    used_ids |= get_new_work(fandom_page, used_ids)
                
                query.pop()     #remove the fandom part of the query
    
    return used_ids


def get_author_bookmarks(work_data, used_ids):
    """
    Given information about a work on AO3, prints a list of similar works that have been bookmarked by the author(s)
    of the original work and returns a set containing the IDs of all the works recc'ed thus far
    """
    for author in work_data["author"]:
        if not author or not author[-1]:  #if the author is anonymous/orphan_account or the author has no works bookmarked
            continue
        
        query = QUERY.copy()
        query.append(('pseud_id', author[2]))
        query.append(('user_id', author[3]))

        rec_count = len(used_ids)
        if "relationship" in work_data:
            used_ids |= filter_bookmarks(work_data, used_ids, "relationship", query)    #for each relationship, goal is to rec 1 bookmarked fic ft. that same relationship

        if len(used_ids) == rec_count:  #if author has bookmarked no works with the same relationships, rec bookmarks from the same fandom
            used_ids |= filter_bookmarks(work_data, used_ids, "fandom", query)
    
    return used_ids


def get_user_bookmarks(work_data, used_ids, max_recs=5):
    """
    Given information about a work on AO3, prints a list of similar works that have been also bookmarked by users that
    bookmarked the original work and returns a set containing the IDs of all the works recc'ed thus far

    max_recs is an optional argument that specifies the maximum number of users to get recommendations from
    """
    bookmark_page = get_soup(work_data["url"][:-len(VIEW_ADULT)] + "/bookmarks")     #get page with list of users who bookmarked original work
    rec_count = 0

    while True:
        for user in bookmark_page.find(class_="bookmark index group").contents:
            if user == "\n" or "id" in user.attrs:
                continue

            user_info = get_user_info(user.a["href"])
            user_bookmark_page = get_soup(get_link_info(user.a)[1] + "/bookmarks")

            if get_number_of_works(user_bookmark_page, user_page=True):    #if user has more than 1 work (i.e. the original work) bookmarked
                query = QUERY.copy()
                query.append(('pseud_id', user_info[0]))
                query.append(('user_id', user_info[1]))

                prev_len = len(used_ids)
                if "relationship" in work_data:   #if the original work has at least 1 relationship tag
                    used_ids |= filter_bookmarks(work_data, used_ids, "relationship", query, min_bookmark_count=1)
                else:   #if the original work has no relationship tags, filter based on fandom instead
                    used_ids |= filter_bookmarks(work_data, used_ids, "fandom", query, min_bookmark_count=1)
                rec_count += len(used_ids) - prev_len
            
            if rec_count >= max_recs:
                return used_ids
        
        pagination = bookmark_page.find(id="main").find("ol", title="pagination")
        if pagination is not None and pagination.find(rel="next") is not None:  #if a next page exists
            next_page_link = get_link_info(pagination.find(rel="next"))[1]
            bookmark_page = get_soup(next_page_link)
        else:
            return used_ids


def get_tag_works(work_data, used_ids, max_recs=5):
    """
    Given information about a work on AO3, prints a list of works with similar tags and returns a set containing the IDs
    of all the works recc'ed thus far

    max_recs is an optional argument that specifies the maximum number of recommendations to give
    """
    query = QUERY.copy()
    query.append(('work_search[sort_column]', 'kudos_count'))
    query.append(('tag_id', work_data["fandom"][0]))

    for info_type in work_data:
        if type(work_data[info_type]) == list and info_type != "author":
            for tag in work_data[info_type]:
                if tag in TAG_IDS[info_type]:
                    query.append(('include_work_search[' + info_type + '_ids]', TAG_IDS[info_type][tag]))
    
    rec_count = 0
    while rec_count < max_recs:
        tagged_works_page = get_soup(DOMAIN + "/works?" + urlencode(query))
        prev_len = len(used_ids)
        
        for _ in range(min(max_recs - rec_count, get_number_of_works(tagged_works_page) - 1)):
            used_ids |= get_new_work(tagged_works_page, used_ids)

        rec_count += len(used_ids) - prev_len
        
        query.pop()
        if len(query) <= 2:
            break
        
    return used_ids


def get_recs(url):
    """
    Given a URL for a work on AO3, prints a list of similar works
    """
    work_data = get_work_data(url)
    used_ids = {work_data["id"]}    #set of all work IDs that have already been seen
    used_ids |= get_author_works(work_data, used_ids)
    used_ids |= get_author_bookmarks(work_data, used_ids)
    used_ids |= get_user_bookmarks(work_data, used_ids)
    used_ids |= get_tag_works(work_data, used_ids)
        

if __name__ == "__main__":
    print("Enter a URL for a work on AO3 or type 'exit()' to quit the program")
    user_input = input(">>> ")
    while user_input != "exit()":
        get_recs(user_input)
        print("Enter a URL for a work on AO3 or type 'exit()' to quit the program")
        user_input = input(">>> ")