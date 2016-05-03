'''
@author: hanan
'''

import sys
import argparse
import urlparse
import syncano
from syncano.models.classes import Class
import requests, json
import os

def python_to_camel_case(class_name, capital):
        parts = class_name.split('_')
        result = ''
        part0 = parts[0]
        if capital:
            result+=(part0.lower().capitalize())
        else:
            result+=(part0.lower())
        for p in parts[1:]:
            result+=(p.lower().capitalize())
        return result

class SyncanoJavaClassTemplate:
    def __init__(self,package_name):
        self.package_name = package_name
        self.FILTER_INDEX_FIELD_ATTR = 'filter_index'
        self.ORDER_INDEX_FIELD_ATTR = 'order_index'  
    def get_class_paragraph(self, CapitalCamelName, syncano_name, json_schema):
        return '%s\n%s\n%s\n%s {%s\n}'%(self.get_package_line(),self.get_imports_paragraph(),\
                                    self.get_class_header_attr(syncano_name), self.get_class_header(CapitalCamelName),\
                                    self.make_class_body(json_schema)
                                     )
    
    def parse_boolean_attr(self,json_obj,attr):
        if attr in json_obj:
                if json_obj[attr]:
                    return True
        return False
        
    def make_class_body(self,json_schema):
        result = ''
        const_field_names = ''
        fields = ''
        for field in json_schema:
            filter_index = self.parse_boolean_attr(field, self.FILTER_INDEX_FIELD_ATTR)
            order_index =self.parse_boolean_attr(field, self.ORDER_INDEX_FIELD_ATTR)
            name = field['name']
            type= field['type']
            ref_type = None
            if type == 'reference':
                ref_type = field['target']
            [field_name, field_name_header] = self.make_field_name(name)
            const_field_names+= '\n\t%s'%field_name_header
            fields+='\n'
            fields+=(self.make_field_field(name,filter_index,order_index,type,ref_type, field_name))
        result = '\n%s%s\n'%(const_field_names,fields)    
        return result
    def make_field_name(self,name):
        field_name = 'FIELD_%s'%name.upper()
        field_name_header =  'private static final String %s = "%s";'%(field_name,name)
        return field_name, field_name_header
    def make_field_field_attr(self,field_name,filter_index,order_index):
        return '@SyncanoField(name = %s, filterIndex = %s, orderIndex = %s)'%(field_name,\
                    'true' if filter_index else 'false',\
                    'true' if order_index else 'false')
    def make_field_field_field(self,type,ref_type,name):
        return 'public %s %s;'%(self.syncano_type_to_java_type(type,ref_type),\
                                python_to_camel_case(name, False))
    def make_field_field(self,name,filter_index,order_index,type,ref_type,field_name):
        return '\n\t%s\n\t%s'%(self.make_field_field_attr(field_name,filter_index,order_index),\
                           self.make_field_field_field(type,ref_type,name))
    def syncano_type_to_java_type(self,type,ref_type):
        syncano_type_to_java_type_dict = {'string': 'String',\
                                          'text': 'String',\
                                          'integer':'Integer',\
                                          'float':'Float',
                                          'boolean':'Boolean',\
                                          'datetime':'Date',\
                                          'file':'File',\
                                          }
        if type == 'reference':
            return python_to_camel_case(ref_type, True)
        else:
            return syncano_type_to_java_type_dict[type]
        
    def get_class_header_attr(self, class_name):
        return '@SyncanoClass(name = "%s")'%class_name
    def get_class_header(self,CapitalCamelName):
        return "public class %s extends SyncanoObject "%(CapitalCamelName)
    
    def get_package_line(self):
        return 'package %s;'%(self.package_name)
    def get_imports_paragraph(self):
        return  """
import com.syncano.library.annotation.SyncanoClass;
import com.syncano.library.annotation.SyncanoField;
import com.syncano.library.data.SyncanoObject;
import java.util.Date;
        """

#A class to note if the class created, changed, or unchanged, or does not exist
class SyncanoJavaClassStatus:
    def __init__(self,filename,CapitalCamelName, syncano_name,status):
        self.syncano_name = syncano_name
        self.status = status
        self.filename = filename
        self.CapitalCamelName = CapitalCamelName
        #at first we only look which class exists, which does not, which
        #'unchanged','changed','created','removed or unrelated',
    def status_code_to_desc(self):
        status_code_to_desc_dict = { \
                1 : 'changed',\
                2 : 'created',\
                3: 'removed or unrelated',
                4: 'not a @syncanoClass. skipping. '}
        return status_code_to_desc_dict[self.status] 

class SyncanoJavaClassGenerator:
    def __init__(self, api_key, class_url, dest_folder, package ):
        self.api_key = api_key
        self.url_components = urlparse.urlparse(class_url)
        self.dest_folder = dest_folder
        self.templateMaker = SyncanoJavaClassTemplate(package)
    def _generate(self):
        self.get_list_of_classes()
        self.check_dst_folder()
        self.compare_folder_and_syncano_classes()
        self.create_or_change_files()
    def get_list_of_classes(self):
        list_of_classes = []
        headers = { "X-API-KEY" : self.api_key }
        response = requests.get(self.url_components.geturl(), headers=headers)
        response.raise_for_status()
        data = response.json()
        objects = data.get('objects')
        for class_obj in objects:
            name = class_obj.get('name')
            list_of_classes.append(name)
        self.list_of_class_syncano = list_of_classes
    def check_dst_folder(self):
        indir = self.dest_folder
        folder_class_stats = dict()
        for f in os.listdir(indir):
            if os.path.isdir(os.path.join(indir,f)) is True:
                continue
            #is this a java file ?>
            filename, file_extension = os.path.splitext(f)
            if not file_extension == '.java':
                folder_class_stats[f]=SyncanoJavaClassStatus(f,f,'',3)
                continue
            #check if not a @syncanoClass
            fff = open(os.path.join(indir,f),'r')
            content = fff.read()
            fff.close()
            index_attr = content.find("@SyncanoClass")
            if index_attr < 0:
                folder_class_stats[filename]=SyncanoJavaClassStatus(f,filename,'',4)
            else:
                folder_class_stats[filename]=SyncanoJavaClassStatus(f,filename,'',3)
        self.folder_class_stats= folder_class_stats
    def compare_folder_and_syncano_classes(self):
        
        for class_name in self.list_of_class_syncano:
            camelName = python_to_camel_case(class_name, True)
            if camelName in self.folder_class_stats:
                if self.folder_class_stats[camelName].status != 4:
                    self.folder_class_stats[camelName].status = 1
                    self.folder_class_stats[camelName].syncano_name = class_name
            else:
                self.folder_class_stats[camelName] = SyncanoJavaClassStatus(camelName+'.java',  camelName,class_name,2)
    def create_or_change_files(self):
        for stats in self.folder_class_stats.values():
            if stats.status != 1 and stats.status != 2:
                continue
            if stats.status == 1:
                os.remove(os.path.join(self.dest_folder,stats.filename))
            json_schema = self.get_syncano_metadata_for_class(stats.syncano_name)
            text = self.templateMaker.get_class_paragraph( stats.CapitalCamelName,stats.syncano_name, json_schema)
            fff = open(os.path.join(self.dest_folder,stats.filename),'w') 
            fff.write(text)
            fff.close()   
            
    def get_syncano_metadata_for_class(self, class_name):
#         connection = syncano.connect(self.api_key)
#         connection.get_model_by_name("polished-night-6282")
#         Instance = connection.Instance
#         pl62 = Instance.please.get("polished-night-6282")
#         connection.get_schema("date_plan")
#         dp = pl62.please.get("date_plan")
#         query = Class.
        headers = { "X-API-KEY" : self.api_key }
        class_schema_url = self.url_components.geturl()+class_name+'/'
        response = requests.get(class_schema_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        schema = data.get('schema')
        return schema
if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog="sjcg",description="Generate Java class for Syncano class")
    parser.add_argument("api_key",metavar="API-KEY", type=str, help="The API-KEY used to retrieve class metadata." )
    parser.add_argument("class_url",metavar="CLASS-URL", type=str, help="Full URL to the Syncano class or to the classes endpoint.")
    parser.add_argument("dest_folder", metavar="DESTINATION-FOLDER",type=str,help="Path create the Java classes at.")
    parser.add_argument("package", metavar="PACKAGE", type=str, help="package for the Java classes.")

    #parser.print_help()
    
    args = parser.parse_args(sys.argv[1:])
    syncanoJavaClassGenerator = SyncanoJavaClassGenerator(args.api_key,args.class_url, args.dest_folder, args.package)
    syncanoJavaClassGenerator._generate()



    
    #parser.parse_args(args, namespace)
