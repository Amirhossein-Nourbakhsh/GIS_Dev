# ----------------------------------------------------------------------------------------------------------
# DESCRIPTION: Downloads US SLR Data.
# SOURCE: https://coast.noaa.gov/slrdata/
# AUTHOR: AWONG
# CREATED: 20200901
# UPDATED: 20200901
# NOTE: Please check if there is enough storage space before running script to download files!!!
#       All zip files combined are about 2GB in total.
# ----------------------------------------------------------------------------------------------------------
require 'nokogiri'
require 'watir'
require 'open-uri'
require 'mechanize'
require 'selenium'
require 'selenium-webdriver'
require 'fileutils'
require 'down'
# ----------------------------------------------------------------------------------------------------------

url = "https://coast.noaa.gov/slrdata/"

# CREATES FOLDER IN YOUR DOWNLOAD DIRECTORY IF IT DOES NOT EXIST
basepath = ("C:/Users/awong/Downloads/SLR/").gsub!("/", "\\")
foldername = Time.new.strftime("%Y_%m_%d")
dirpath = basepath + foldername + "\\_RAW\\"

unless File.directory?(dirpath)
    FileUtils.mkdir_p(dirpath)
else
    puts "_________Skipped create directory, already exist."
end

# BROWSER DEFAULTS
profile = Selenium::WebDriver::Firefox::Profile.new
profile.native_events = false
profile['browser.download.folderList'] = 2
profile['browser.download.dir'] = dirpath
profile['browser.helperApps.neverAsk.saveToDisk'] = "image/jpeg,text/csv,application/pdf,application/vnd.ms-excel"

# OPEN BROWSER
begin
    browser = Watir::Browser.new :firefox, :profile => profile
    browser.goto url
rescue
    sleep 2 
    retry
end
sleep 2

page = Nokogiri::HTML(browser.html)
table = page.css("div[class='panel-group']").css("div[class='panel panel-default ng-scope ng-isolate-scope']")
i = 0
table.each do |state|
    puts "----------------------------------------"
    statename = state.css("h4[class='panel-title']").text.strip
    puts statename
    statetable = state.css("div[class='panel-collapse collapse']").css("div[class='panel-body']").css("div[class='ng-scope']")
    statetable.each do |row|
        cities = row.css("h4").text.strip
        link = "https:" + row.css("ul").css("li")[0].css("a").first["href"].to_s.strip
        puts "#{i+=1}. #{link}"

        # DOWNLOAD FILES
        fileURL = Down.download(link)
        sleep 1 until File.exist? (fileURL)
        fileURL.close
        FileUtils.mv(fileURL.path, dirpath + "#{fileURL.original_filename}")
    end
end

# CLOSE EVERYTHING
sleep 2
browser.close

puts "-------------------------------------------------------"
puts i
puts Time.now.to_s + "\n" + "DONE! Double check."