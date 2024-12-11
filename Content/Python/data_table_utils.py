import unreal
import re

def is_row_type(dt:unreal.DataTable, type)->bool:
    row_type:unreal.ScriptStruct = dt.get_editor_property("row_struct")
    return row_type == type

def find_row_idx(dt:unreal.DataTable, row_name:str)->int:
    row_idx = -1
    row_names = unreal.DataTableFunctionLibrary.get_data_table_row_names(dt)
    for i in range(len(row_names)):
        if row_names[i] == row_name:
            row_idx = i
            break
        
    return row_idx

def cell(dt:unreal.DataTable, row_name:str, col_name:str)->tuple[bool,str]:
    row_idx = find_row_idx(dt, row_name)
    if row_idx == -1:
        return False, f"{dt}不存在{row_name}的数据行"
    
    cols = unreal.DataTableFunctionLibrary.get_data_table_column_as_string(dt, col_name)
    if(len(cols)<=0):
        return False, f"{dt}不存在{col_name}的数据列"
    
    if(row_idx >= len(cols)):
        return False, f"{dt}不存在{row_name}的数据行"
    
    return True, cols[row_idx]

def str_to_text(val:str)->tuple[bool, str]:
    # NSLOCTEXT("[98D26E67444B21D6FFDB3B90C3345A4F]", "9FF0878945ABD7FA2D6010B94E70CABD", "疫苗公示风险点")
    match = re.search('NSLOCTEXT\("\[[\w]+\]", "[\w]+", "([^"]*)"\)', val)
    if match and len(match.groups())>0:
        return (True, match.group(1))
    else:
        # 处理为string table引用的情况
        # LOCTABLE("/FSK/DataTable/FSStringTable.FSStringTable", "FX-Ttitle")
        match2 = re.search('LOCTABLE\("([^\"]+)", "([^\"]+)"\)', val)
        if match2:
            tbl = match2.group(1)
            key = match2.group(2)
            s = unreal.StringTableLibrary.get_table_entry_source_string(tbl, key)
            if s == "" or s.strip() == "":
                return (False, "")
            return (True, s)
        return (False, "")
    
def str_to_enum_name(val:str)->tuple[bool, str]:
    # Click
    match = re.search('^[^\."\'\(\)]+$', val)
    if match:
        return (True, match.string)
    else:
        return (False, "")

def str_to_data_table_handle(val:str)->tuple[bool, unreal.DataTableRowHandle]:
    # (DataTable=/Script/Engine.DataTable\'"/CRB/Data/Scene/DT_CRB_HealthCommissionZone.DT_CRB_HealthCommissionZone"\',RowName="预防接种")
    match_path = re.search("DataTable=.*?'\"([^\"]+?)\.", val)
    match_row = re.search("RowName=\"(.+?)\"", val)
    if match_path and match_row and len(match_path.groups())>0 and len(match_row.groups())>0:
        pkg = match_path.group(1)
        row = match_row.group(1)
        dt = unreal.EditorAssetLibrary.load_asset(pkg)
        return (True, unreal.DataTableRowHandle(dt, row))
    else:
        return (False, None)
    
def data_table_handle_is_valid( handle:unreal.DataTableRowHandle)->bool:
    if handle.data_table == None:
        return False
    if find_row_idx(handle.data_table, handle.row_name) < 0:
        return False
    
    return True

def data_table_handle_array_is_valid(handles:list[unreal.DataTableRowHandle])->tuple[bool,int]:
    i = 0
    for h in handles:
        if not data_table_handle_is_valid(h):
            return (False, i)
        i+=1
    
    return (True, -1)

def str_to_str_array(val:str)->tuple[bool, list[str]]:
    # # ((DisplayName=NSLOCTEXT("[E41DFCCE417D31E7238512921CE971E1]", "E03A2E914090A2BE1AFD9E8E14E5295F", "无风险"),Content=(DataTable=/Script/Engine.DataTable'"/ZSCJ/Data/CheckContent/DT_ZSCJ_CheckContent_Image.DT_ZSCJ_CheckContent_Image"',RowName="劳动者合同告知风险点检查风险点-无_1")),(DisplayName=NSLOCTEXT("[E41DFCCE417D31E7238512921CE971E1]", "5245E3CB4A217E2A237388806CC78B72", "有风险"),Content=(DataTable=/Script/Engine.DataTable'"/ZSCJ/Data/CheckContent/DT_ZSCJ_CheckContent_Image.DT_ZSCJ_CheckContent_Image"',RowName="劳动者合同告知风险点检查风险点-有_1")))
    if not val.startswith('(') or not val.endswith(')'):
        return (False, [])
    
    ret:list[str] = []
    val = val[1:-1]
    line = ""
    wait_close = 0
    for char in val:
        if char == '(':
            wait_close += 1
            line += char
        elif char == ')':
            wait_close -= 1
            line += char
            if wait_close < 0:
                unreal.log_error(f"解析为数组失败:{val}")
                return (False, [])
        elif char == ',':
            if wait_close == 0:
                ret.append(line.strip())
                line = ""
            else:
                line += char
        else:
            line += char
    
    line = line.strip()
    if len(line)>0:
        ret.append(line.strip())
        line = ""
    return [True,ret]
    
    
def str_to_data_table_handle_array(val:str)->tuple[bool, list[unreal.DataTableRowHandle]]:
    
    success, lines = str_to_str_array(val)
    if not success:
        return (False, [])
    
    handle_array : list[unreal.DataTableRowHandle] = []
    for line in lines:
        success, handle = str_to_data_table_handle(line)
        if not success:
            return (False, [])
        else:
            handle_array.append(handle)
        
    return (True, handle_array)

def str_to_prop_array(val:str)->tuple[bool, dict[str,str]]:
    '''将一行属性解析为属性列表'''
    # (DisplayName=NSLOCTEXT("[E41DFCCE417D31E7238512921CE971E1]", "E03A2E914090A2BE1AFD9E8E14E5295F", "无风险"),Content=(DataTable=/Script/Engine.DataTable'"/ZSCJ/Data/CheckContent/DT_ZSCJ_CheckContent_Image.DT_ZSCJ_CheckContent_Image"',RowName="劳动者合同告知风险点检查风险点-无_1")),
    if not val.startswith('(') or not val.endswith(')'):
        return (False, {})
    
    ret:dict[str,str] = {}
    val = val[1:-1]
    line = ""
    wait_close = 0
    for char in val:
        if char == '(':
            wait_close += 1
            line += char
        elif char == ')':
            wait_close -= 1
            line += char
            if wait_close < 0:
                unreal.log_error(f"解析为数组失败:{val}")
                return (False, {})
        elif char == ',':
            if wait_close == 0:
                idx = line.find('=') # 以第一个等号分割为键值对
                if idx>0 and idx < len(line):
                    ret[line[0:idx].strip()] = line[idx+1:].strip()
                    line = ""
                else:
                    unreal.log_error(f"解析属性错误:{line}")
                    return (False, {}) 
            else:
                line += char
        else:
            line += char
    
    line = line.strip()
    if len(line)>0:
        idx = line.find('=') # 以第一个等号分割为键值对
        if idx>0 and idx < len(line):
            ret[line[0:idx].strip()] = line[idx+1:].strip()
            line = ""
        else:
            unreal.log_error(f"解析属性错误:{line}")
            return (False, {}) 
    return [True,ret]