import requests
from bs4 import BeautifulSoup
import csv
import time

# Constants
BASE_URL = "https://medex.com.bd"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Function to scrape the details page
def scrape_details_page(link):
    try:
        response = requests.get(link, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Remove unwanted sections like nav, header, footer, script, and style
        for tag in soup(['nav', 'header', 'footer', 'script', 'style']):
            tag.decompose()
        
        # Extract all plain text from the page
        plain_text = soup.get_text(separator="\n").strip()
        return plain_text
    except Exception as e:
        print(f"Error scraping details from {link}: {e}")
        return "N/A"

# Function to scrape a single page and write to the CSV and text files
def scrape_page_to_files(page_number, csv_writer, text_file):
    try:
        url = f"{BASE_URL}/brands?page={page_number}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        medicines = soup.find_all("a", class_="hoverable-block")
        print(f"Found {len(medicines)} medicines on page {page_number}")
        
        for medicine in medicines:
            link = medicine['href']
            if not link.startswith("http"):
                link = BASE_URL + link
            
            medname = medicine.find("div", class_="col-xs-12 data-row-top").text.strip()
            medtype = medicine.find("img", class_="dosage-icon")
            medtype = medtype["alt"].strip() if medtype else "N/A"
            
            # Weight
            weight_div = medicine.find("div", class_="col-xs-12 data-row-strength")
            weight = weight_div.text.strip() if weight_div else "N/A"
            
            # Generic name
            generic_div = medicine.find_all("div", class_="col-xs-12")
            generic_name = generic_div[2].text.strip() if len(generic_div) >= 3 else "N/A"
            
            # Company
            company_span = medicine.find("span", class_="data-row-company")
            company = company_span.text.strip() if company_span else "N/A"
            
            # Scrape details from the linked page
            details = scrape_details_page(link)
            
            # Write the structured data to the CSV file
            csv_writer.writerow([medname, medtype, weight, generic_name, company, link, details])
            
            # Write the plain HTML to the text file
            text_file.write(f"{link},\"{medicine.prettify()}\"\n")
            
            # Include a delay to prevent overwhelming the server
            time.sleep(1)
    except Exception as e:
        print(f"Error scraping page {page_number}: {e}")

# Main function
def main():
    csv_output_file = "medicines_data.csv"
    text_output_file = "medicines_data.txt"
    total_pages = 1 # Adjust this to scrape multiple pages
    
    with open(csv_output_file, mode="w", newline="", encoding="utf-8") as csv_file, \
         open(text_output_file, mode="w", encoding="utf-8") as text_file:
        
        csv_writer = csv.writer(csv_file)
        # Write the header row for the CSV
        csv_writer.writerow(["Medicine Name", "Type", "Weight", "Generic Name", "Company", "Link", "Details"])
        
        # Scrape pages and save to both files
        for page_number in range(1, total_pages + 1):
            print(f"Scraping page {page_number}...")
            scrape_page_to_files(page_number, csv_writer, text_file)
    
    print(f"Data scraping complete. CSV saved to {csv_output_file}, HTML saved to {text_output_file}")

# Run the script
if __name__ == "__main__":
    main()
