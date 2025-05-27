import os
import re
import shutil
import logging
import xml.etree.ElementTree as ElementTree
import zipfile

from xml.etree import ElementTree

class STIGParser:
    def __init__(self, filename):
        if not filename.endswith('.zip'):
            raise Exception("File must end in .zip")
        if not os.path.isfile(filename):
            raise FileNotFoundError(f"{stig_zip} is unable to be found")
        if not zipfile.is_zipfile(filename):
            raise Exception("Not a ZIP file")
        self.zip = zipfile.ZipFile(filename, 'r')
        self.filename = filename[:-4]

    def list_stigs(self) -> list:
        logging.debug("called")
        output = []
        stigs = self.zip.namelist()
        for stig in stigs:
            stig_filename = stig.split('/')[-1]
            if stig_filename.endswith('.zip'):
                entry = self.pretty_name(stig_filename)
                output.append(entry)
        return output

    def list_versions(self, stig: str) -> list:
        logging.debug(f"called for {stig}")
        output = []
        stig_filename = self.zip_name(stig)
        with zipfile.ZipFile(self.zip.open(f"{self.filename}/{stig_filename}")) as zip_stig:
            filepaths = zip_stig.namelist()
            logging.debug(filepaths)
            for filepath in filepaths:
                if zipfile.Path(zip_stig, at=filepath).is_dir():
                    entry = self.pretty_name(filepath)
                    entry = entry[:-1]
                    output.append(entry)
            # TEMPORARY WORK-AROUND FOR SPEC Innovations Folder (directory not showing in namelist)
            if len(output) == 0:
                for filepath in filepaths:
                    if "/" in filepath:
                        folder = filepath.split('/')[0]
                        if folder not in output:
                            entry = self.pretty_name(folder)
                            output.append(entry)
        return output

    def get_stig(self, stig: str, version: str) -> str:
        logging.debug(f"called for {stig} : {version}")
        stig_filename = self.zip_name(stig)
        version_filename = self.version_name(version)
        with zipfile.ZipFile(self.zip.open(f"{self.filename}/{stig_filename}")) as zip_stig:
            filepaths = zip_stig.namelist()
            for filepath in filepaths:
                if filepath.startswith(version_filename) and filepath.endswith(".xml"):
                    with zip_stig.open(f"{filepath}") as f:
                        file_output = (f.read())
                        output = file_output.decode("utf-8")
        return output

    def pretty_name(self, zipname) -> str:
        output = re.sub(r"(\.zip)$", "", zipname)
        output = re.sub(r"^(U_)", "", output)
        output = re.sub(r"_", " ", output)
        return output

    def zip_name(self, prettyname) -> str:
        output = re.sub(r" ", "_", prettyname)
        output = re.sub(r"^", "U_", output)
        output = re.sub(r"$", ".zip", output)
        return output

    def version_name(self, prettyname: str) -> str:
        output = re.sub(r" ", "_", prettyname)
        output = re.sub(r"^", "U_", output)
        return output

    def file_name(self, prettyname) -> str:
        output = re.sub(r" ", "_", prettyname)
        output = re.sub(r"^", "U_", output)
        output = re.sub(r"(\_Manual_STIG)$", "", output)
        output = re.sub(r"_(?=[a-zA-Z0-9]+$)","_STIG_", output)
        output = re.sub(r"$","_Manual-xccdf.xml", output)
        return output

    def parse_stig(self, stig_data: str) -> dict:
        root = ElementTree.fromstring(stig_data)
        ns = re.match(r'\{.*\}', root.tag)[0]
        output = {"title": root.find(f"./{ns}title").text}
        output["status"] = { "date": root.find(f"./{ns}status").attrib["date"],
                             "status": root.find(f"./{ns}status").text}
        output["description"] = root.find(f"./{ns}description").text
        output["rules"] = []
        output_groups = root.findall(f"./{ns}Group")
        for group in output_groups:
            output_group = {}
            output_group["group_id"] = group.attrib["id"]
            output_group["rule_id"] = re.sub(r"_rule$", "", group.find(f"./{ns}Rule").attrib["id"])
            output_group["stig_id"] = group.find(f"./{ns}Rule/{ns}version").text
            output_group["srg_id"] = group.find(f"./{ns}title").text
            output_group["severity"] = group.find(f"./{ns}Rule").attrib["severity"]
            output_group["legacy_id"] = []
            legacy_ids = group.findall(f"./{ns}Rule/{ns}ident[@system='http://cyber.mil/legacy']")
            for legacy_id in legacy_ids:
                output_group["legacy_id"].append(legacy_id.text)
            output_group["reference_id"] = []
            reference_ids = group.findall(f"./{ns}Rule/{ns}ident[@system='http://cyber.mil/cci']")
            for reference_id in reference_ids:
                output_group["reference_id"].append(reference_id.text)
            output_group["rule_title"] = group.find(f"./{ns}Rule/{ns}title").text
            output_group["description"] = group.find(f"./{ns}Rule/{ns}description").text
            output_group["fix_text"] = group.find(f"./{ns}Rule/{ns}fixtext").text
            output_group["fix_check"] = group.find(f"./{ns}Rule/{ns}check/{ns}check-content").text
            output["rules"].append(output_group)
        return output        

    def close(self):
        self.zip.close()

if __name__ == "__main__":
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(f'./'))
    rule_template = env.get_template("rule.j2")
    log_format = '%(asctime)s:%(levelname)8.7s:%(module)11.10s:%(funcName)16.15s: %(message)s'
    logging.basicConfig(format=log_format,level=logging.INFO)
    logging.debug("Begin CLI interaction")
    working_dir = os.getcwd()
    stig_viewer = STIGParser("U_SRG-STIG_Library_April_2025.zip")
    stigs = stig_viewer.list_stigs()
    for i in stigs:
        print(i)
    usr_stig = input("Enter STIG to view: ")
    if usr_stig in stigs:
        folders = stig_viewer.list_versions(usr_stig)
        for i in folders:
            print(i)
        usr_version = input("Enter Version to view: ")
        if usr_version in folders:
            file = stig_viewer.get_stig(usr_stig, usr_version)
            stig_dict = stig_viewer.parse_stig(file)
            rule_md = rule_template.render(rule = stig_dict["rules"][0])
            print(rule_md)
            '''
            for key, value in stig_dict["rules"][0].items():
                print("#"*20)
                print(f"#{key:^18}#")
                print(f"#"*20)
                print(value)
            '''
    stig_viewer.close()
