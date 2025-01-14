import re
import gc
import pandas as pd
import numpy as np
from itertools import repeat
from multiprocessing import  Pool
from liftover import get_lifter
from functools import partial
from gwaslab.vchangestatus import vchange_status
from gwaslab.vchangestatus import status_match
from gwaslab.vchangestatus import change_status
from gwaslab.Log import Log
from gwaslab.CommonData import get_chr_to_number
from gwaslab.CommonData import get_number_to_chr
from gwaslab.CommonData import get_chr_list
from gwaslab.datatype_check import check_datatype
#fixID
#rsidtochrpos
#remove_dup
#fixchr
#fixpos
#fixallele
#normalizeallele
#normalizevariant
#checkref
#sanitycheckstats
#flipallelestats
#parallelizeassignrsid
#sortcoordinate
#sortcolumn

###############################################################################################################
# 20220514 

def fixID(sumstats,
       snpid="SNPID",rsid="rsID",chrom="CHR",pos="POS",nea="NEA",ea="EA",status="STATUS",
       fixchrpos=False,fixid=False,fixeanea=False,fixeanea_flip=False,fixsep=False,
       overwrite=False,verbose=True,forcefixid=False,log=Log()):  
    '''
    1. fx SNPid
    2. fix chr and pos using snpid
    3. checking rsid and chr:pos:nea:ea
    '''
    if verbose: log.write("Start to check IDs...")
    if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns))   
    
    check_col(sumstats,[snpid,rsid],status)
    
    ############################  checking ###################################################  
    if snpid in sumstats.columns:  
        if verbose: log.write(" -Checking if SNPID is chr:pos:ref:alt...(separator: - ,: , _)")
        #is_chrposrefalt = sumstats[snpid].str.match(r'(chr)?([0-9XYMT]+)[:_-]([0-9]+)[:_-]([ATCG]+)[:_-]([ATCG]+)', case=False, flags=0, na=False)
        is_chrposrefalt = sumstats[snpid].str.match(r'^\w+[:_-]\d+[:_-][ATCG]+[:_-][ATCG]+$', case=False, flags=0, na=False)
        is_snpid_na = sumstats[snpid].isna()
        sumstats.loc[ is_chrposrefalt,status] = vchange_status(sumstats.loc[ is_chrposrefalt,status],3 ,"975" ,"630")
        sumstats.loc[(~is_chrposrefalt)&(~is_snpid_na),status] = vchange_status(sumstats.loc[(~is_chrposrefalt)&(~is_snpid_na),status],3 ,"975" ,"842")
        
    if rsid in sumstats.columns: 
        if verbose: log.write(" -Checking if rsID is rsxxxxxx or RSxxxxxxx...")
        is_rsid = sumstats[rsid].str.startswith(r'rs',na=False)
        
        sumstats.loc[ is_rsid,status] = vchange_status(sumstats.loc[ is_rsid,status], 3, "986","520")
        sumstats.loc[~is_rsid,status] = vchange_status(sumstats.loc[~is_rsid,status], 3, "986","743")
        
        if verbose: log.write(" -Checking if chr:pos:ref:alt is mixed in rsID column ...")
        is_rs_chrpos = sumstats[rsid].str.match(r'^\w+[:_-]\w+[:_-]\w+[:_-]\w+$', case=False, flags=0, na=False)
        #is_rs_chrpos = sumstats[rsid].str.match(r'(chr)?([0-9XYMT]+)[:_-]([0-9]+)[:_-]([ATCG]+)[:_-]([ATCG]+)', case=False, flags=0, na=False)
        
        if verbose: log.write(" -Number of chr:pos:ref:alt mixed in rsID column :",sum(is_rs_chrpos))
        if verbose: log.write(" -Number of Unrecognized rsID :",len(sumstats) - sum(is_rs_chrpos) - sum(is_rsid) ) 
        if verbose: log.write(" -A look at the unrecognized rsID :",set(sumstats.loc[(~is_rsid)&(~is_rs_chrpos),rsid].head()),"...") 
      
    ############################  fixing chr pos###################################################  
    if fixchrpos is True:
    # from snpid or rsid, extract chr:pos to fix CHR and POS    
        if snpid in sumstats.columns: 
            if verbose: log.write(" -Fixing CHR and POS...")
            if overwrite is True: 
                if verbose: log.write(" -Overwrite is applied...")
                # fix all
                to_fix = is_chrposrefalt
                
                #fix variants with chr and pos being empty
            elif (chrom in sumstats.columns) and (pos in sumstats.columns) :
                to_fix = is_chrposrefalt & sumstats[chrom].isna() & sumstats[pos].isna()
                to_fix_num = sum(to_fix)
                if to_fix_num and verbose: log.write(" -Number of variants could be fixed: "+str(to_fix_num)+" ...")
                elif verbose: log.write(" -No fixable variants. ...")
            
            elif (chrom not in sumstats.columns) and (pos in sumstats.columns):
                if verbose: log.write(" -Initiating CHR columns...")
                sumstats.loc[:,chrom]=pd.Series(dtype="string")   
                to_fix = is_chrposrefalt & sumstats[chrom].isna() & sumstats[pos].isna()
                to_fix_num = sum(to_fix)
                if to_fix_num>0 and verbose: log.write(" -Number of variants could be fixed: "+str(to_fix_num)+" ...")
                elif verbose: log.write(" -No fixable variants. ...")
            
            elif (chrom in sumstats.columns) and (pos not in sumstats.columns):
                if verbose: log.write(" -Initiating CHR and POS column...")
                sumstats.loc[:,pos]=pd.Series(dtype="Int64") 
                to_fix = is_chrposrefalt & sumstats[chrom].isna() & sumstats[pos].isna() 
                to_fix_num = sum(to_fix)
                if to_fix_num>0 and verbose: log.write(" -Number of variants could be fixed: "+str(to_fix_num)+" ...")
                elif verbose: log.write(" -No fixable variants. ...")     
            else:
                if verbose: log.write(" -Initiating CHR and POS columns...")
                sumstats.loc[:,chrom]=pd.Series(dtype="string")   
                sumstats.loc[:,pos]=pd.Series(dtype="Int64") 
                to_fix = is_chrposrefalt
                to_fix_num = sum(to_fix)
                if to_fix_num>0 and verbose: log.write(" -Number of variants could be fixed: "+str(to_fix_num)+" ...")
                elif verbose: log.write(" -No fixable variants. ...")   
                    
            if sum(to_fix)>0:
                if verbose: log.write(" -Filling CHR and POS columns using valid SNPID's chr:pos...")
                # format and qc filled chr and pos
               
                sumstats.loc[to_fix,chrom] = sumstats.loc[to_fix,snpid].str.split(':|_|-',n=2).str.get(0)
                sumstats.loc[to_fix,pos] = sumstats.loc[to_fix,snpid].str.split(':|_|-',n=2).str.get(1)
                
                #sumstats.loc[to_fix,chrom] = sumstats.loc[to_fix,snpid].str.split(':|_|-').str[0].str.strip("chrCHR").astype("string")
                #sumstats.loc[to_fix,pos] =np.floor(pd.to_numeric(sumstats.loc[to_fix,snpid].str.split(':|_|-').str[1], errors='coerce')).astype('Int64')
                # change status
                #sumstats.loc[to_fix,status] = vchange_status(sumstats.loc[to_fix,status], 4, "98765432","00000000")    
        
        if rsid in sumstats.columns:
            if verbose: log.write(" -Fixing CHR and POS using chr:pos:ref:alt format variants in rsID column...")
            if overwrite is True: 
                if verbose: log.write(" -Overwrite is applied...")
                to_fix = is_rs_chrpos
            elif (chrom in sumstats.columns) and (pos in sumstats.columns) :
                to_fix = is_rs_chrpos & sumstats[chrom].isna() & sumstats[pos].isna()
                if sum(to_fix)>0 and verbose: log.write(" -Number of variants could be fixed: "+str(sum(to_fix))+" ...")
                elif verbose: log.write(" -No fixable variants ...")
            elif (chrom not in sumstats.columns) and (pos in sumstats.columns):
                if verbose: log.write(" -Initiating CHR columns...")
                sumstats.loc[:,chrom]=pd.Series(dtype="string")   
                to_fix = is_rs_chrpos & sumstats[chrom].isna() & sumstats[pos].isna()
                if sum(to_fix)>0 and verbose: log.write(" -Number of variants could be fixed: "+str(sum(to_fix))+" ...")
                elif verbose: log.write(" -No fixable variants ...")
            elif (chrom in sumstats.columns) and (pos not in sumstats.columns):
                if verbose: log.write(" -Initiating CHR and POS column...")
                sumstats.loc[:,pos]=pd.Series(dtype="Int64") 
                to_fix = is_rs_chrpos & sumstats[chrom].isna() & sumstats[pos].isna() 
                if sum(to_fix)>0 and verbose: log.write(" -Number of variants could be fixed: "+str(sum(to_fix))+" ...")
                elif verbose: log.write(" -No fixable variants ...")
            else:
                if verbose: log.write(" -Initiating CHR and POS columns...")
                sumstats.loc[:,chrom]=pd.Series(dtype="string")   
                sumstats.loc[:,pos]=pd.Series(dtype="Int64") 
                to_fix = is_rs_chrpos
                if sum(to_fix)>0 and verbose: log.write(" -Number of variants could be fixed: "+str(sum(to_fix))+" ...")
                elif verbose: log.write(" -No fixable variants ...")   
            
            if sum(to_fix)>0:    
                if verbose: log.write(" -Filling CHR and POS columns using chr:pos:ref:alt format variants in rsID column...")
                sumstats.loc[to_fix,chrom] = sumstats.loc[to_fix,rsid].str.split(':|_|-',n=2).str[0]
                sumstats.loc[to_fix,pos] = sumstats.loc[to_fix,rsid].str.split(':|_|-',n=2).str[1]
                #sumstats.loc[to_fix,pos] = np.floor(pd.to_numeric(sumstats.loc[to_fix,rsid].str.split(':|_|-',x).get(1), errors='coerce')).astype('Int64')
                #sumstats.loc[to_fix,status] = vchange_status(sumstats.loc[to_fix,status], 4, "98765432","00000000").astype("string")  
                
    ############################  fixing chr pos###################################################   
    #if fixeanea is True:
    #    if verbose: log.write(" -Warning: Please make sure a1 is ref or not in Chr:pos:a1:a2")
    #    if overwrite is True:
    #        if verbose: log.write(" -Overwrite is applied...")
    #        to_fix = is_chrposrefalt
    #    elif (nea in sumstats.columns) and (nea in sumstats.columns):
    #        to_fix = is_chrposrefalt&(sumstats[nea].isna()|sumstats[ea].isna())
    #        if sum(to_fix)>0 and verbose: log.write(" -Number of variants could be fixed: "+str(sum(to_fix))+" ...")
    #    elif (nea in sumstats.columns) and (ea not in sumstats.columns):
    #        if verbose: log.write(" -Initiating EA columns...")
    #        sumstats[ea]=pd.Series(dtype="string")
    #        to_fix = is_chrposrefalt&(sumstats[nea].isna()|sumstats[ea].isna())
    #        if sum(to_fix)>0 and verbose: log.write(" -Number of variants could be fixed: "+str(sum(to_fix))+" ...")
    #    elif (nea not in sumstats.columns) and (ea in sumstats.columns):
    #        if verbose: log.write(" -Initiating NEA columns...")
    #        sumstats[nea]=pd.Series(dtype="string")
    #        to_fix = is_chrposrefalt&(sumstats[nea].isna()|sumstats[ea].isna())
    #        if sum(to_fix)>0 and verbose: log.write(" -Number of variants could be fixed: "+str(sum(to_fix))+" ...")
    #    else:
    #        if verbose: log.write(" -Initiating EA and NEA columns...")
    #        sumstats[nea]=pd.Series(dtype="string")
    #        sumstats[ea]=pd.Series(dtype="string")
    #        to_fix = is_chrposrefalt
    #        if sum(to_fix)>0: 
    #            if verbose: log.write(" -Number of variants could be fixed: "+str(sum(to_fix))+" ...")
    #                
    #    if sum(to_fix)>0:    
    #        if verbose: log.write(" -Filling "+str(sum(to_fix))+" EA and NEA columns using SNPID's chr:pos:nea:ea...")
    #        
    #        if fixeanea_flip is True:
    #            if verbose: log.write(" -Flipped : chr:pos:a1:a2...a1->EA , a2->NEA ")
    #            sumstats.loc[to_fix,ea] = sumstats.loc[to_fix,snpid].apply(lambda x:re.split(':|_|-',x)[2]).astype("string")  
    #            sumstats.loc[to_fix,nea] = sumstats.loc[to_fix,snpid].apply(lambda x:re.split(':|_|-',x)[3]).astype("string")
    #        else:
    #            if verbose: log.write(" -Chr:pos:a1:a2...a1->EA , a2->NEA ")
    #            sumstats.loc[to_fix,ea] = sumstats.loc[to_fix,snpid].apply(lambda x:re.split(':|_|-',x)[3]).astype("string")  
    #            sumstats.loc[to_fix,nea] = sumstats.loc[to_fix,snpid].apply(lambda x:re.split(':|_|-',x)[2]).astype("string")
    #        #to_change_status = sumstats[status].str.match(r"\w\w\w[45]\w\w\w")
    #        #sumstats.loc[to_fix&to_change_status,status] = vchange_status(sumstats.loc[to_fix&to_change_status,status],4,"2")  
    #        #sumstats.loc[to_fix,snpid].apply(lambda x:re.split(':|_|-',x)[1]).astype("string")
    #        #sumstats.loc[to_fix,rsid].apply(lambda x:re.split(':|_|-',x)[1]).astype("Int64")
    
    ############################  fixing id ################################################### 
    if fixsep is True:
        if snpid in sumstats.columns: 
            if verbose: log.write(' -Replacing [_-] in SNPID with ":" ...')
            sumstats.loc[:,snpid] = sumstats.loc[:,snpid].str.replace(r"[_-]",":",regex=True)

    if fixid is True:
        if snpid not in sumstats.columns: 
        # initiate a SNPID column
            sumstats.loc[:,snpid]=pd.Series(dtype="string")
        
        if (rsid in sumstats.columns) and (sum(is_rs_chrpos)>0) :
            sumstats.loc[:,snpid]= sumstats.loc[is_rs_chrpos,rsid]
            
        if (chrom in sumstats.columns) and (pos in sumstats.columns):
            #only fix when CHR and POS is available
            pre_number=sum(sumstats[snpid].isna())                                
            
            if overwrite is False:
                #fix empty 
                to_fix = sumstats[snpid].isna() & sumstats[status].str.match( r"\w\w\w[0]\w\w\w", case=False, flags=0, na=False ) 
                #status_match(sumstats[status],4,0)
                #
            else:
                #fix all
                to_fix = sumstats[status].str.match( r"\w\w\w[0]\w\w\w", case=False, flags=0, na=False ) 
                # status_match(sumstats[status],4,0)
                #
            
            if (ea in sumstats.columns) and (nea in sumstats.columns):
            # when ea and nea is available  -> check status -> fix to chr:pos:nea:ea 
                
                pattern = r"\w\w\w[0]\w\w\w"  
                matched_index = sumstats[status].str.match(pattern)
                #matched_index = status_match(sumstats[status],4,0) #
                to_part_fix = matched_index & to_fix 
                
                #pattern = r"\w\w\w[0][01267][01234]\w"  
                pattern = r"\w\w\w\w[0123][01267][01234]"
                matched_index = sumstats[status].str.match(pattern)
                #status_match(sumstats[status],5,[0,1,2,3]) | status_match(sumstats[status],6,[0,1,2,6,7])| status_match(sumstats[status],7,[0,1,2,3,4])
                #
                if forcefixid is True:
                    matched_index = to_fix
                to_full_fix = matched_index & to_fix 
                
                
                if sum(to_part_fix)>0:
                    sumstats.loc[to_part_fix,snpid] = sumstats.loc[to_part_fix,chrom].astype("string") + ":"+sumstats.loc[to_part_fix,pos].astype("string")
                if sum(to_full_fix)>0:
                    sumstats.loc[to_full_fix,snpid] = sumstats.loc[to_full_fix,chrom].astype("string") + ":"+sumstats.loc[to_full_fix,pos].astype("string") +":"+ sumstats.loc[to_full_fix,nea].astype("string") +":"+ sumstats.loc[to_full_fix,ea].astype("string")
                if verbose: log.write(" -Filling "+str(sum(to_part_fix)-sum(to_full_fix)) +" SNPID using CHR:POS...")
                if verbose: log.write(" -Filling "+str(sum(to_full_fix)) +" SNPID using CHR:POS:NEA:EA...")
                sumstats.loc[(to_full_fix),status] = vchange_status(sumstats.loc[(to_full_fix),status],3,"975","630") 
                sumstats.loc[(to_part_fix),status] = vchange_status(sumstats.loc[(to_part_fix),status],3,"975","842")  
                
            else:
            #when these is no ea or ena, just fix to chr:pos
                to_part_fix = to_fix & sumstats[chrom].notnull() & sumstats[pos].notnull()
                if verbose: log.write(" -Filling "+str(sum(to_part_fix)) +" SNPID using CHR POS...")
                if sum(to_part_fix)>0:
                    sumstats.loc[to_part_fix,snpid] = sumstats.loc[to_part_fix,chrom].astype("string") + ":"+sumstats.loc[to_part_fix,pos].astype("string")
                    sumstats.loc[to_part_fix,status] = vchange_status(sumstats.loc[(to_part_fix),status],3,"975","842")
                    
            after_number=sum(sumstats[snpid].isna())
            if verbose: log.write(" -Fixed "+ str(pre_number - after_number) +" variants ID...")
        elif verbose: log.write(" -ID unfixable: no CHR and POS columns or no SNPID. ")
    if verbose: log.write("Finished checking IDs successfully!")
    return sumstats

""


###############################################################################################################
# 20230128 
def removedup(sumstats,mode="dm",chrom="CHR",pos="POS",snpid="SNPID",ea="EA",nea="NEA",rsid="rsID",keep='first',keep_col="P",remove=False,keep_ascend=True,verbose=True,log=Log()):
    '''
    remove duplicate SNPs based on 1. SNPID,
    remove duplicate SNPs based on 2. CHR, POS, EA, and NEA
    remove duplicate SNPs based on 3. rsID
    remove multiallelic SNPs based on 4. CHR, POS
    '''
    
    # sort the variants using the specified column before removing
    if keep_col is not None : 
        if keep_col in sumstats.columns:
            if verbose: log.write("Start to sort the sumstats using " + keep_col +"...")
            sumstats = sumstats.sort_values(by=keep_col,ascending=keep_ascend)
        else:
            if verbose: log.write("Column" + keep_col +" was not detected... skipping... ")
    total_number = len(sumstats)  
    
    # remove by duplicated SNPID
    if (snpid in sumstats.columns) and "d" in mode:
        if verbose: log.write("Start to remove duplicated variants based on snpid...")
        if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns)) 
        if verbose: log.write(" -Which variant to keep: ",  keep )   
        pre_number =len(sumstats)   
        if snpid in sumstats.columns:
            # keep na and remove duplicated
            sumstats = sumstats.loc[sumstats[snpid].isna() | (~sumstats.duplicated(subset=[snpid], keep=keep)),:]
            after_number=len(sumstats)   
            if verbose:  log.write(" -Removed ",pre_number -after_number ," based on SNPID...")
    
    # remove by duplicated rsID
    if (rsid in sumstats.columns) and ("d" in mode):
        # keep na and remove duplicated
        pre_number =len(sumstats)
        if verbose: log.write("Start to remove duplicated variants based on rsID...")
        sumstats = sumstats.loc[sumstats[rsid].isna() | (~sumstats.duplicated(subset=rsid, keep=keep)),:]
        after_number=len(sumstats)   
        if verbose:  log.write(" -Removed ",pre_number -after_number ," based on rsID...")
    
    # remove by duplicated variants by CHR:POS:NEA:EA
    if (chrom in sumstats.columns) and (pos in sumstats.columns) and (nea in sumstats.columns) and (ea in sumstats.columns) and "d" in mode:
        if verbose: log.write("Start to remove duplicated variants based on CHR,POS,EA and NEA...")
        if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns)) 
        if verbose: log.write(" -Which variant to keep: ",  keep )   
        pre_number =len(sumstats)   
        if snpid in sumstats.columns:
            # keep na and remove duplicated
            sumstats = sumstats.loc[(~sumstats[[chrom,pos,ea,nea]].all(axis=1)) | (~sumstats.duplicated(subset=[chrom,pos,ea,nea], keep=keep)),:]
            after_number=len(sumstats)   
            if verbose:  log.write(" -Removed ",pre_number -after_number ," based on CHR,POS,EA and NEA...") 
    
    # remove by multiallelic variants by CHR:POS
    if (chrom in sumstats.columns) and (pos in sumstats.columns) and "m" in mode:
        # keep na and remove duplicated
        pre_number =len(sumstats) 
        if verbose: log.write("Start to remove multiallelic variants based on chr:pos...")    
        if verbose: log.write(" -Which variant to keep: ",  keep ) 
        sumstats = sumstats.loc[(~sumstats.loc[:,[chrom,pos]].all(axis=1)) | (~sumstats.duplicated(subset=[chrom,pos], keep=keep)),:]
        after_number=len(sumstats)  
        if verbose:  log.write(" -Removed ",pre_number -after_number," multiallelic variants...")   
    after_number=len(sumstats)   
    
    # resort the coordinates
    if verbose:  log.write(" -Removed ",total_number -after_number," variants in total.")
    if keep_col is not None : 
        if verbose: log.write(" -Sort the coordinates...")
        sumstats = sortcoordinate(sumstats,verbose=False)
    
    if remove is True:
        # if remove==True, remove NAs
        if verbose: log.write(" -Removing NAs...")
        pre_number =len(sumstats) 
        sumstats = sumstats.loc[~sumstats.isna().any(axis=1),:]
        after_number=len(sumstats) 
        if verbose:  log.write(" -Removed ",pre_number -after_number," variants with NA values.")  
    if verbose: log.write("Finished removing successfully!")
    return sumstats

###############################################################################################################
# 20230128
def fixchr(sumstats,chrom="CHR",status="STATUS",add_prefix="",x=("X",23),y=("Y",24),mt=("MT",25), remove=False, verbose=True, chrom_list = None, minchr=1,log=Log()):
        #chrom_list = get_chr_list() #bottom 
        if chrom_list is None:
            chrom_list = get_chr_list()
        if check_col(sumstats,chrom,status) is not True:
            if verbose: log.write(".fix_chr: Specified not detected..skipping...")
            return sumstats
        if verbose: log.write("Start to fix chromosome notation...")
        if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns))          
        
        # convert to string datatype
        try:
            if verbose: log.write(" -Checking CHR data type...")
            if sumstats.loc[:,chrom].dtype == "string":
                pass
            else:
                sumstats.loc[:,chrom] = sumstats.loc[:,chrom].astype("string")
        except:
            if verbose: log.write(" -Force converting to pd string data type...")
            sumstats.loc[:,chrom] = sumstats.loc[:,chrom].astype("string")
        
        # check if CHR is numeric
        is_chr_fixed = sumstats[chrom].str.isnumeric()
        # fill NAs with False
        is_chr_fixed = is_chr_fixed.fillna(False)
        if verbose: log.write(" -Variants with standardized chromosome notation:",sum(is_chr_fixed))  
        
        # if there are variants whose CHR need to be fixed
        if sum(is_chr_fixed)<len(sumstats):
            
            #extract the CHR number or X Y M MT
            chr_extracted = sumstats.loc[~is_chr_fixed,chrom].str.extract(r'(chr)?([0-9]{1,3}|[XYM]|MT)$',flags=re.IGNORECASE|re.ASCII)[1]
            is_chr_fixable = ~chr_extracted.isna()
            if verbose: log.write(" -Variants with fixable chromosome notations:",sum(is_chr_fixable))  

            # For not fixed variants, check if na
            is_chr_na  = sumstats.loc[~is_chr_fixed, chrom].isna()
            if sum(is_chr_na)>0 and verbose: 
                log.write(" -Variants with NA chromosome notations:",sum(is_chr_na))  
            
            # Check variants with CHR being not NA and not fixable
            is_chr_invalid = (~is_chr_fixable)&(~is_chr_na)
            if sum(is_chr_invalid)>0 and verbose: 
                log.write(" -Variants with invalid chromosome notations:",sum(is_chr_invalid)) 
                log.write(" -Invalid chromosome notations converted to NA :" , set(sumstats.loc[~sumstats[chrom].isin(chrom_list),chrom].head()))
            elif verbose:
                log.write(" -No unrecognized chromosome notations...")
            
            # Assign good chr back to sumstats
            sumstats.loc[is_chr_fixable.index,chrom] = chr_extracted[is_chr_fixable.index]

            # X, Y, MT to 23,24,25
            xymt_list = [x[0].lower(),y[0].lower(),mt[0].lower(),x[0].upper(),y[0].upper(),mt[0].upper()]
            
            # check if sumstats contain sex CHR
            sex_chr = sumstats[chrom].isin(xymt_list)
            
            # if sumstats contain sex CHR
            if sum(sex_chr)>0:
                if verbose: log.write(" -Identifying non-autosomal chromosomes : {}, {}, and {} ...".format(x[0],y[0],mt[0]))
                if verbose: log.write(" -Identified ",str(sum(sex_chr))," variants on sex chromosomes...")
                
                # convert "X, Y, MT" to numbers
                convert_num_to_xymt={}
                if x[0].lower() in sumstats[chrom].values or x[0].upper() in sumstats[chrom].values:
                    convert_num_to_xymt[x[0].lower()] = str(x[1])
                    convert_num_to_xymt[x[0].upper()] = str(x[1])
                    if verbose: log.write(" -Standardizing sex chromosome notations: {} to {}...".format(x[0], x[1]))
                if y[0].lower() in sumstats[chrom].values or y[0].upper() in sumstats[chrom].values:
                    convert_num_to_xymt[y[0].lower()] = str(y[1])
                    convert_num_to_xymt[y[0].upper()] = str(y[1])
                    if verbose: log.write(" -Standardizing sex chromosome notations: {} to {}...".format(y[0], y[1]))
                if mt[0].lower() in sumstats[chrom].values or mt[0].upper() in sumstats[chrom].values:
                    convert_num_to_xymt[mt[0].lower()] = str(mt[1])
                    convert_num_to_xymt[mt[0].upper()] = str(mt[1])
                    if verbose: log.write(" -Standardizing sex chromosome notations: {} to {}...".format(mt[0], mt[1]))
                sumstats.loc[sex_chr,chrom] =sumstats.loc[sex_chr,chrom].map(convert_num_to_xymt)
            
            # change status code
            sumstats.loc[is_chr_fixed,status] = vchange_status(sumstats.loc[is_chr_fixed,status],4,"986","520")
            if len(is_chr_fixable.index)>0:
                sumstats.loc[is_chr_fixable.index,status] = vchange_status(sumstats.loc[is_chr_fixable.index,status],4,"986","520")
            if len(is_chr_fixable.index)>0:
                sumstats.loc[is_chr_invalid.index,status] = vchange_status(sumstats.loc[is_chr_invalid.index,status],4,"986","743")
            
            # check variants with unrecognized CHR
            unrecognized_num = sum(~sumstats[chrom].isin(chrom_list))
            if (remove is True) and unrecognized_num>0:
                # remove variants with unrecognized CHR 
                if verbose: log.write(" -Removed "+ str(unrecognized_num)+ " variants with unrecognized chromosome notations.") 
                #sumstats = sumstats.loc[sumstats.index[sumstats[chrom].isin(chrom_list)],:]
                good_chr = sumstats[chrom].isin(chrom_list)
                sumstats = sumstats.loc[good_chr, :].copy()
        else:
            if verbose: log.write(" -All CHR are already fixed...") 
            sumstats.loc[is_chr_fixed,status] = vchange_status(sumstats.loc[is_chr_fixed,status],4,"986","520")
        
        # Convert string to int
        try:
            sumstats.loc[:,chrom] = sumstats.loc[:,chrom].astype('Int64')
        except:
            # force convert
            sumstats.loc[:,chrom] = np.floor(pd.to_numeric(sumstats.loc[:,chrom], errors='coerce')).astype('Int64')
        
        # filter out variants with CHR <=0
        if verbose: log.write(" -Sanity check for CHR...") 
        
        out_of_range_chr = sumstats[chrom] < minchr
        out_of_range_chr = out_of_range_chr.fillna(False)
        
        if verbose:log.write(" -Removed {} varaints with CHR < {}...".format(sum(out_of_range_chr),minchr))
        
        sumstats = sumstats.loc[~out_of_range_chr,:]

        if verbose: log.write("Finished fixing chromosome notation successfully!")
        return sumstats

###############################################################################################################    
# 20230128
def fixpos(sumstats,pos="POS",status="STATUS",remove=False, verbose=True,limit=250000000, log=Log()):
        if check_col(sumstats,pos,status) is not True:
            if verbose: log.write(".fix_pos: Specified not detected..skipping...")
            return sumstats
        if verbose: log.write("Start to fix basepair positions...")
        if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns))   
        
        all_var_num = len(sumstats)
        #convert to numeric
        is_pos_na = sumstats.loc[:,pos].isna()
        
        # check if POS is string
        if pd.api.types.is_string_dtype(sumstats[pos]):
            # if so, remove thousands separator
            if verbose: log.write(' -Removing thousands separator "," or underbar "_" ...')
            sumstats.loc[~is_pos_na, pos] = sumstats.loc[~is_pos_na, pos].astype("string").str.replace(",|_", "",regex=True)

        # convert POS to integer
        try:
            if verbose: log.write(' -Converting to Int64 data type ...')
            sumstats.loc[:,pos] = sumstats.loc[:,pos].astype('Int64')
        except:
            if verbose: log.write(' -Force converting to Int64 data type ...')
            sumstats.loc[:,pos] = np.floor(pd.to_numeric(sumstats.loc[:,pos], errors='coerce')).astype('Int64')
        
        is_pos_fixed = ~sumstats.loc[:,pos].isna()
        is_pos_invalid = (~is_pos_na)&(~is_pos_fixed)
        
        sumstats.loc[is_pos_fixed,status]   = vchange_status(sumstats.loc[is_pos_fixed,status]  ,4,"975","630")
        sumstats.loc[is_pos_invalid,status] = vchange_status(sumstats.loc[is_pos_invalid,status],4,"975","842")
        
        # remove outlier, limit:250,000,000
        if verbose: log.write(" -Position upper_bound is: " + "{:,}".format(limit))
        out_lier=(sumstats[pos]>limit) & (~is_pos_na)
        if verbose: log.write(" -Remove outliers:",sum(out_lier))
        sumstats = sumstats.loc[~out_lier,:]
        
        #remove na
        if remove is True: 
            sumstats = sumstats.loc[~sumstats[pos].isna(),:]
            remain_var_num = len(sumstats)
            if verbose: log.write(" -Removed "+str(all_var_num - remain_var_num)+" variants with bad positions.")        
        
        if verbose: log.write(" -Converted all position to datatype Int64.")
        if verbose: log.write("Finished fixing basepair position successfully!")
        return sumstats

###############################################################################################################    
# 20220514
def fixallele(sumstats,ea="EA", nea="NEA",status="STATUS",remove=False,verbose=True,log=Log()):
        # remove variants with alleles other than actgACTG
        if check_col(sumstats,ea,nea,status) is not True:
            if verbose: log.write("EA and NEA not detected..skipping...")
            return sumstats
        if verbose: log.write("Start to fix alleles...")
        if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns))   
        
        #if (ea not in sumstats.columns) or (nea not in sumstats.columns):
        if verbose: log.write(" -Converted all bases to string datatype and UPPERCASE.")
        categories = set(sumstats.loc[:,ea].str.upper())|set(sumstats.loc[:,nea].str.upper())|set("N")
        sumstats.loc[:,ea]=pd.Categorical(sumstats[ea].str.upper(),categories = categories) 
        sumstats.loc[:,nea]=pd.Categorical(sumstats[nea].str.upper(),categories = categories) 
        all_var_num = len(sumstats)
        
        ## check ATCG
        bad_ea = sumstats[ea].str.contains("[^actgACTG]",na=True)
        bad_nea = sumstats[nea].str.contains("[^actgACTG]",na=True)
        good_ea  = ~bad_ea
        good_nea = ~bad_nea
        
        ## check NA
        is_eanea_na = sumstats[ea].isna() |  sumstats[nea].isna()
        
        ## check same alleles
        not_variant = sumstats[nea] == sumstats[ea]
        
        ## sum up invalid variants
        is_invalid = bad_ea | bad_nea | not_variant
        
        exclude  = bad_nea | bad_ea
        
        if verbose: 
            if len(set(sumstats.loc[bad_ea,ea].head())) >0:
                log.write(" -A look at the non-ATCG EA:",set(sumstats.loc[bad_ea,ea].head()),"...") 
            if len(set(sumstats.loc[bad_nea,nea].head())) >0:
                log.write(" -A look at the non-ATCG NEA:",set(sumstats.loc[bad_nea,nea].head()),"...") 
        
        if remove is True:
            sumstats = sumstats.loc[(good_ea & good_nea),:].copy()
            if verbose: log.write(" -Removed "+str(sum(exclude))+" variants with alleles that contain bases other than A/C/T/G .")  
        else:
            sumstats.loc[:,[ea,nea]] = sumstats.loc[:,[ea,nea]].fillna("N")
            if verbose: log.write(" -Detected "+str(sum(exclude))+" variants with alleles that contain bases other than A/C/T/G .") 
        categories = set(sumstats.loc[:,ea].str.upper())|set(sumstats.loc[:,nea].str.upper())|set("N")
        sumstats.loc[:,ea]=pd.Categorical(sumstats[ea].str.upper(),categories = categories) 
        sumstats.loc[:,nea]=pd.Categorical(sumstats[nea].str.upper(),categories = categories) 
        
        is_eanea_fixed = good_ea | good_nea
        is_snp = (sumstats[ea].str.len()==1) &(sumstats[nea].str.len()==1)
        is_indel = (sumstats[ea].str.len()!=sumstats[nea].str.len())
        is_not_normalized = (sumstats[ea].str.len()>1) &(sumstats[nea].str.len()>1)
        is_normalized = is_indel &( (sumstats[ea].str.len()==1) &(sumstats[nea].str.len()>1) | (sumstats[ea].str.len()>1) &(sumstats[nea].str.len()==1) )
        
        if sum(is_invalid)>0:
            sumstats.loc[is_invalid, status]                      = vchange_status(sumstats.loc[is_invalid,status],                5,"9","6") 
        if sum(is_eanea_na)>0:
            sumstats.loc[is_eanea_na,status]                      = vchange_status(sumstats.loc[is_eanea_na, status],              5,"9","7")
        if sum(is_eanea_fixed&is_not_normalized)>0:
            sumstats.loc[is_eanea_fixed&is_not_normalized,status] = vchange_status(sumstats.loc[is_eanea_fixed&is_not_normalized,status], 5,"9","5")
        if sum(is_eanea_fixed&is_snp)>0:
            sumstats.loc[is_eanea_fixed&is_snp, status]           = vchange_status(sumstats.loc[is_eanea_fixed&is_snp,status],        5,"9","0")
        if sum(is_eanea_fixed&is_indel)>0:
            sumstats.loc[is_eanea_fixed&is_indel,status]          = vchange_status(sumstats.loc[is_eanea_fixed&is_indel, status],      5,"9","4")
        if sum(is_eanea_fixed&is_normalized)>0:
            sumstats.loc[is_eanea_fixed&is_normalized,status]     = vchange_status(sumstats.loc[is_eanea_fixed&is_normalized, status],  5,"4","3")
        gc.collect()
        if verbose: log.write("Finished fixing allele successfully!")
        return sumstats

###############################################################################################################   
# 20220721

def parallelnormalizeallele(sumstats,snpid="SNPID",rsid="rsID",pos="POS",nea="NEA",ea="EA" ,status="STATUS",n_cores=1,verbose=True,log=Log()):
    if check_col(sumstats,pos,ea,nea,status) is not True:
        if verbose: log.write("WARNING:.normalize(): specified columns not detected..skipping...")
        return sumstats
    
    if verbose: log.write("Start to normalize variants...")
    if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns))   
    #variants_to_check = status_match(sumstats[status],5,[4,5]) #
    #r'\w\w\w\w[45]\w\w'
    variants_to_check = sumstats[status].str[4].str.match(r'4|5', case=False, flags=0, na=False)
    if sum(variants_to_check)==0:
        if verbose: log.write(" -No available variants to normalize..")
        if verbose: log.write("Finished normalizing variants successfully!")
        return sumstats
    ###############################################################################################################
    if sum(variants_to_check)>0:
        if sum(variants_to_check)<10000: 
            n_cores=1  
        pool = Pool(n_cores)
        map_func = partial(normalizeallele,pos=pos,nea=nea,ea=ea,status=status)
        df_split = np.array_split(sumstats.loc[variants_to_check,[pos,nea,ea,status]], n_cores)
        normalized_pd = pd.concat(pool.map(map_func,df_split))
        pool.close()
        pool.join()
    ###############################################################################################################
    
    if verbose:
        before_normalize = sumstats.loc[variants_to_check,[ea,nea]]
        changed_num = len(normalized_pd.loc[(before_normalize[ea]!=normalized_pd[ea]) | (before_normalize[nea]!=normalized_pd[nea]),:])
        if changed_num>0:
            if snpid in sumstats.columns:
                before_normalize_id = sumstats.loc[variants_to_check,snpid]
            elif rsid in sumstats.columns:
                before_normalize_id = sumstats.loc[variants_to_check,rsid]
            
            log.write(" -Not normalized allele IDs:",end="")
            for i in before_normalize_id.loc[(before_normalize[ea]!=normalized_pd[ea]) | (before_normalize[nea]!=normalized_pd[nea])].head().values:
                log.write(i,end=" ",show_time=False)
            log.write("... \n",end="",show_time=False) 

            log.write(" -Not normalized allele:",end="")
            for i in before_normalize.loc[(before_normalize[ea]!=normalized_pd[ea]) | (before_normalize[nea]!=normalized_pd[nea]),[ea,nea]].head().values:
                log.write(i,end="",show_time=False)
            log.write("... \n",end="",show_time=False)     
            log.write(" -Modified "+str(changed_num) +" variants according to parsimony and left alignment principal.")
        else:
            log.write(" -All variants are already normalized..")
    ###################################################################################################################
    categories = set(sumstats.loc[:,ea])|set(sumstats.loc[:,nea]) |set(normalized_pd.loc[:,ea]) |set(normalized_pd.loc[:,nea])
    sumstats.loc[:,ea]  = pd.Categorical(sumstats.loc[:,ea],categories = categories) 
    sumstats.loc[:,nea] = pd.Categorical(sumstats.loc[:,nea],categories = categories ) 
    sumstats.loc[variants_to_check,[pos,nea,ea,status]] = normalized_pd.values
    try:
        sumstats.loc[:,pos] = sumstats.loc[:,pos].astype('Int64')
    except:
        sumstats.loc[:,pos] = np.floor(pd.to_numeric(sumstats.loc[:,pos], errors='coerce')).astype('Int64')
  
    if verbose: log.write("Finished normalizing variants successfully!")
    return sumstats

def normalizeallele(sumstats,pos="POS" ,nea="NEA",ea="EA",status="STATUS"):
    #single df
    normalized = sumstats.apply(lambda x: normalizevariant(x[0],x[1],x[2],x[3]),axis=1)
    sumstats = pd.DataFrame(normalized.to_list(), columns=[pos,nea,ea,status],index=sumstats.index)
    return sumstats

def normalizevariant(pos,a,b,status):
    # single record
    # https://genome.sph.umich.edu/wiki/Variant_Normalization
    # a - ref - nea    starting -> pos
    # b - alt - ea
    # status xx1xx /xx2xx /xx9xx
    
    status_pre=status[:4]
    status_end=status[5:]
    
    if len(a)==1 or len(b)==1:
        #return pos,a,b,change_status(status,5,0) #status_pre+"0"+status_end
        return pos,a,b,status_pre+"0"+status_end
    pos_change=0
    pointer_a_l, pointer_a_r = 0, len(a)-1
    pointer_b_l, pointer_b_r = 0, len(b)-1

    #remove from right
    for i in range(max(len(a),len(b))):
        if a[pointer_a_r] == b[pointer_b_r]:
            pointer_a_r-=1
            pointer_b_r-=1
        else:
            break
        if pointer_a_r-pointer_a_l==0 or pointer_b_r-pointer_b_l==0:
            if len(a)==1 or len(b)==1:
                return pos,a[pointer_a_l:pointer_a_r+1],b[pointer_b_l:pointer_b_r+1],status_pre+"0"+status_end #change_status(status,5,0) #
            return pos,a[pointer_a_l:pointer_a_r+1],b[pointer_b_l:pointer_b_r+1],status_pre+"3"+status_end #change_status(status,5,3) #

    # remove from left
    for i in range(max(len(a),len(b))):

        if a[pointer_a_l] == b[pointer_b_l]:
            pointer_a_l+=1
            pointer_b_l+=1
            pos_change+=1
        else:
            break
        if pointer_a_r-pointer_a_l==0 or pointer_b_r-pointer_b_l==0:
            break
    if len(a)==1 or len(b)==1:
        return pos+pos_change,a[pointer_a_l:pointer_a_r+1],b[pointer_b_l:pointer_b_r+1],status_pre+"0"+status_end #change_status(status,5,0) #
    return pos+pos_change,a[pointer_a_l:pointer_a_r+1],b[pointer_b_l:pointer_b_r+1],status_pre+"3"+status_end # change_status(status,5,3) #
""


###############################################################################################################
# 20220426
def sanitycheckstats(sumstats,
                     coltocheck=None,
                     n=(0,2**31-1),
                     ncase=(0,2**31-1),
                     ncontrol=(0,2**31-1),
                     eaf=(0,1),
                     mac=(0,2**31-1),
                     chisq=(0,float("Inf")),
                     z=(-37.5,37.5),
                     f=(0,float("Inf")),
                     p=(5e-300,1.000001),
                     mlog10p=(0,9999),
                     beta=(-10,10),
                     se=(0,float("Inf")),
                     OR=(0,10),
                     OR_95L=(0,float("Inf")),
                     OR_95U=(0,float("Inf")),
                     HR=(-10,10),
                     HR_95L=(0,float("Inf")),
                     HR_95U=(0,float("Inf")),
                     info=(0,1.000001),
                     verbose=True,
                     log=Log()):
    '''
    Sanity check:
        N:      Int32    , N>0 , 
        EAF:    float32  , 0<= EAF <=1, 
        P:      float64  , 0< P <5e-300, 
        BETA:   float32  , abs(BETA) <10
        SE:     float32  , SE >0
        OR:     float32  , -10<log(OR)<10
        OR_95L: float32  , OR_95L>0
        OR_95U: float32  , OR_95L>0
        INFO:   float32  , 1>=INFO>0
    '''
    ## add direction
    if coltocheck is None:
        coltocheck = ["P","MLOG10P","INFO","Z","BETA","SE","EAF","CHISQ","F","N","N_CASE","N_CONTROL","OR","OR_95L","OR_95U","HR","HR_95L","HR_95U","STATUS"]
    if verbose: log.write("Start sanity check for statistics ...") 
    if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns))   
    cols_to_check=[]
    oringinal_number=len(sumstats)
    sumstats = sumstats.copy()
    
    ###SAMPLE SIZE################################################################################################################################################
    pre_number=len(sumstats)
    if "N" in coltocheck and "N" in sumstats.columns:
        cols_to_check.append("N")
        if verbose: log.write(" -Checking if ",n[0],"<=N<=",n[1]," ...") 
        sumstats.loc[:,"N"] = np.floor(pd.to_numeric(sumstats.loc[:,"N"], errors='coerce')).astype("Int32")
        sumstats = sumstats.loc[(sumstats["N"]>=n[0]) & (sumstats["N"]<=n[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad N.") 
    pre_number=len(sumstats)
    if "N_CASE" in coltocheck and "N_CASE" in sumstats.columns:
        cols_to_check.append("N_CASE")
        if verbose: log.write(" -Checking if ",ncase[0],"<=N_CASE<=",ncase[1]," ...") 
        sumstats.loc[:,"N_CASE"] = np.floor(pd.to_numeric(sumstats.loc[:,"N_CASE"], errors='coerce')).astype("Int32")
        sumstats = sumstats.loc[(sumstats["N_CASE"]>=ncase[0]) & (sumstats["N_CASE"]<=ncase[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad N_CASE.") 
    pre_number=len(sumstats)
    if "N_CONTROL" in coltocheck and "N_CONTROL" in sumstats.columns:
        cols_to_check.append("N_CONTROL")
        if verbose: log.write(" -Checking if ",ncontrol[0],"<=N_CONTROL<=",ncontrol[1]," ...") 
        sumstats.loc[:,"N_CONTROL"] = np.floor(pd.to_numeric(sumstats.loc[:,"N_CONTROL"], errors='coerce')).astype("Int32")
        sumstats = sumstats.loc[(sumstats["N_CONTROL"]>=ncontrol[0]) & (sumstats["N_CONTROL"]<=ncontrol[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad N_CONTROL.") 
    pre_number=len(sumstats)
    if "N" in coltocheck and "N" in sumstats.columns and "N_CONTROL" in coltocheck and "N_CONTROL" in sumstats.columns and "N_CASE" in coltocheck and "N_CASE" in sumstats.columns:
        if verbose: log.write(" -Checking if N = N_CASE + N_CONTROL ...") 
        matched_n = sumstats.loc[:,"N"] == sumstats.loc[:,"N_CASE"] + sumstats.loc[:,"N_CASE"] 
        sumstats = sumstats.loc[matched_n,:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with N != N_CASE + N_CONTROL.") 

    ###ALLELE FREQUENCY################################################################################################################################################
    pre_number=len(sumstats)    
    if "EAF" in coltocheck and "EAF" in sumstats.columns:
        cols_to_check.append("EAF")
        if verbose: log.write(" -Checking if ",eaf[0],"<EAF<",eaf[1]," ...") 
        sumstats.loc[:,"EAF"] = pd.to_numeric(sumstats.loc[:,"EAF"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["EAF"]>=eaf[0]) & (sumstats["EAF"]<=eaf[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad EAF.") 
    
    pre_number=len(sumstats)    
    if "EAF" in coltocheck and "EAF" in sumstats.columns and "N" in coltocheck and "N" in sumstats.columns:
        if verbose: log.write(" -Checking if ",mac[0],"<=MAC<=",mac[1]," ...") 
        sumstats["_MAF"]=sumstats["EAF"]
        sumstats.loc[sumstats["EAF"]>0.5,"_MAF"] = 1 - sumstats.loc[sumstats["EAF"]>0.5,"EAF"]
        sumstats["_MAC"] = np.floor(pd.to_numeric(sumstats.loc[:,"_MAF"] * sumstats.loc[:,"N"], errors='coerce')).astype("int64")
        macl = ( sumstats["_MAC"] >= mac[0]) 
        macu = ( sumstats["_MAC"] <= mac[1]) 
        sumstats = sumstats.loc[macl&macu,:]
        sumstats = sumstats.drop(labels=["_MAF","_MAC"],axis=1)
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad MAC.") 

    ###TEST STATISTICS################################################################################################################################################
    pre_number=len(sumstats)    
    if "CHISQ" in coltocheck and "CHISQ" in sumstats.columns:
        cols_to_check.append("CHISQ")
        if verbose: log.write(" -Checking if ",chisq[0],"<CHISQ<",chisq[1]," ...") 
        sumstats.loc[:,"CHISQ"] = pd.to_numeric(sumstats.loc[:,"CHISQ"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["CHISQ"]>=chisq[0]) & (sumstats["CHISQ"]<=chisq[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad CHISQ.") 
    
    pre_number=len(sumstats)    
    if "Z" in coltocheck and "Z" in sumstats.columns:
        cols_to_check.append("Z")
        if verbose: log.write(" -Checking if ",z[0],"<Z<",z[1]," ...") 
        sumstats.loc[:,"Z"] = pd.to_numeric(sumstats.loc[:,"Z"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["Z"]>=z[0]) & (sumstats["Z"]<=z[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad Z.") 
    
    pre_number=len(sumstats)    
    if "F" in coltocheck and "F" in sumstats.columns:
        cols_to_check.append("F")
        if verbose: log.write(" -Checking if ",f[0],"<F<",f[1]," ...") 
        sumstats.loc[:,"F"] = pd.to_numeric(sumstats.loc[:,"F"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["F"]>=f[0]) & (sumstats["F"]<=f[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad F.") 

    ###P ################################################################################################################################################
    pre_number=len(sumstats) 
    if "P" in coltocheck and "P" in sumstats.columns:
        cols_to_check.append("P")
        if verbose: log.write(" -Checking if ",p[0],"< P <",p[1]," ...") 
        sumstats.loc[:,"P"] = pd.to_numeric(sumstats.loc[:,"P"], errors='coerce')
        sumstats = sumstats.loc[(sumstats["P"]>=p[0]) & (sumstats["P"]<=p[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad P.") 
    
    pre_number=len(sumstats)
    if "MLOG10P" in coltocheck and "MLOG10P" in sumstats.columns:
        cols_to_check.append("MLOG10P")
        if verbose: log.write(" -Checking if ",mlog10p[0],"<MLOG10P<",mlog10p[1]," ...") 
        sumstats.loc[:,"MLOG10P"] = pd.to_numeric(sumstats.loc[:,"MLOG10P"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["MLOG10P"]>=mlog10p[0]) & (sumstats["MLOG10P"]<=mlog10p[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad MLOG10P.") 
    
    ###EFFECT ################################################################################################################################################
    pre_number=len(sumstats)    
    if "BETA" in coltocheck and "BETA" in sumstats.columns:
        cols_to_check.append("BETA")
        if verbose: log.write(" -Checking if ",beta[0],"<BETA<",beta[1]," ...") 
        sumstats.loc[:,"BETA"] = pd.to_numeric(sumstats.loc[:,"BETA"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["BETA"]>=beta[0]) & (sumstats["BETA"]<=beta[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad BETA.") 
            
    pre_number=len(sumstats)    
    if "SE" in coltocheck and "SE" in sumstats.columns:
        cols_to_check.append("SE")
        if verbose: log.write(" -Checking if ",se[0],"<SE<",se[1]," ...") 
        sumstats.loc[:,"SE"] = pd.to_numeric(sumstats.loc[:,"SE"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["SE"]>=se[0]) & (sumstats["SE"]<=se[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad SE.") 
            
    pre_number=len(sumstats)    
    if "OR" in coltocheck and "OR" in sumstats.columns:
        cols_to_check.append("OR")
        if verbose: log.write(" -Checking if ",OR[0],"<log(OR)<",OR[1]," ...") 
        sumstats.loc[:,"OR"] = pd.to_numeric(sumstats.loc[:,"OR"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(np.log(sumstats["OR"])>OR[0]) & (np.log(sumstats["OR"])<OR[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad OR.") 
            
    pre_number=len(sumstats)   
    if "OR_95L" in coltocheck and "OR_95L" in sumstats.columns:
        cols_to_check.append("OR_95L")
        if verbose: log.write(" -Checking if ",OR_95L[0],"<OR_95L<",OR_95L[1]," ...") 
        sumstats.loc[:,"OR_95L"] = pd.to_numeric(sumstats.loc[:,"OR_95L"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["OR_95L"]>OR_95L[0]) & (sumstats["OR_95L"]<OR_95L[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad OR_95L.") 
            
    pre_number=len(sumstats)    
    if "OR_95U" in coltocheck and "OR_95U" in sumstats.columns:
        cols_to_check.append("OR_95U")
        if verbose: log.write(" -Checking if ",OR_95U[0],"<OR_95U<",OR_95U[1]," ...") 
        sumstats.loc[:,"OR_95U"] = pd.to_numeric(sumstats.loc[:,"OR_95U"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["OR_95U"]>OR_95U[0]) & (sumstats["OR_95U"]<OR_95U[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad OR_95U.") 
    
    pre_number=len(sumstats)    
    if "HR" in coltocheck and "HR" in sumstats.columns:
        cols_to_check.append("HR")
        if verbose: log.write(" -Checking if ",HR[0],"<log(HR)<",HR[1]," ...") 
        sumstats.loc[:,"HR"] = pd.to_numeric(sumstats.loc[:,"HR"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(np.log(sumstats["HR"])>HR[0]) & (np.log(sumstats["HR"])<HR[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad HR.") 
            
    pre_number=len(sumstats)   
    if "HR_95L" in coltocheck and "HR_95L" in sumstats.columns:
        cols_to_check.append("HR_95L")
        if verbose: log.write(" -Checking if ",HR_95L[0],"<HR_95L<",HR_95L[1]," ...") 
        sumstats.loc[:,"HR_95L"] = pd.to_numeric(sumstats.loc[:,"HR_95L"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["HR_95L"]>HR_95L[0]) & (sumstats["HR_95L"]<HR_95L[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad HR_95L.") 
            
    pre_number=len(sumstats)    
    if "HR_95U" in coltocheck and "HR_95U" in sumstats.columns:
        cols_to_check.append("HR_95U")
        if verbose: log.write(" -Checking if ",HR_95U[0],"<HR_95U<",HR_95U[1]," ...") 
        sumstats.loc[:,"HR_95U"] = pd.to_numeric(sumstats.loc[:,"HR_95U"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["HR_95U"]>HR_95U[0]) & (sumstats["HR_95U"]<HR_95U[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad HR_95U.") 
    #INFO #################################################################################################################
    pre_number=len(sumstats)    
    if "INFO" in coltocheck and "INFO" in sumstats.columns:
        cols_to_check.append("INFO")
        if verbose: log.write(" -Checking if ",info[0],"<INFO<",info[1]," ...") 
        sumstats.loc[:,"INFO"] = pd.to_numeric(sumstats.loc[:,"INFO"], errors='coerce').astype("float32")
        sumstats = sumstats.loc[(sumstats["INFO"]>=info[0]) & (sumstats["INFO"]<=info[1]),:]
        after_number=len(sumstats)
        if verbose: log.write(" -Removed "+str(pre_number - after_number)+" variants with bad INFO.") 
    ###STATUS ################################################################################################################################################
    pre_number=len(sumstats)    
    if "STATUS" in coltocheck and "STATUS" in sumstats.columns:
        cols_to_check.append("STATUS")
        if verbose: log.write(" -Checking STATUS and converting STATUS to categories....") 
        categories = {str(j+i) for j in [1900000,3800000,9700000,9800000,9900000] for i in range(0,100000)}
        sumstats.loc[:,"STATUS"] = pd.Categorical(sumstats["STATUS"],categories=categories)
    
    pre_number=len(sumstats)  
    sumstats = sumstats.dropna(subset=cols_to_check)
    after_number=len(sumstats)
    if verbose:log.write(" -Dropping {} variants with NAs in the checked columns...".format(pre_number - after_number))

    if verbose: log.write(" -Removed "+str(oringinal_number - after_number)+" variants with bad statistics in total.") 
    if verbose:
        log.write(" -Data types for each column:")
        check_datatype(sumstats,verbose=verbose, log=log)
    if verbose: log.write("Finished sanity check successfully!")
    return sumstats

###############################################################################################################
# 20220426
def get_reverse_complementary_allele(a):
    dic = str.maketrans({
       "A":"T",
       "T":"A",
       "C":"G",
       "G":"C"})
    return a[::-1].translate(dic)

def flip_direction(string):
    flipped_string=""
    for char in string:
        if char=="?":
            flipped_string+="?"
        elif char=="+":
            flipped_string+="-"
        elif char=="-":
            flipped_string+="+"
        else: #sometime it is 0
            flipped_string+=char
    return flipped_string
    
def flipallelestats(sumstats,status="STATUS",verbose=True,log=Log()):
    
    if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns))
    
    ###################get reverse complementary####################
    pattern = r"\w\w\w\w\w[45]\w"  
    #matched_index = status_match(sumstats[status],6,[4,5]) #
    matched_index = sumstats[status].str[5].str.match(r"4|5")
    if sum(matched_index)>0:
        if verbose: log.write("Start to convert alleles to reverse complement for SNPs with status xxxxx[45]x... ") 
        if verbose: log.write(" -Flipping "+ str(sum(matched_index)) +" variants...") 
        if ("NEA" in sumstats.columns) and ("EA" in sumstats.columns) :
            if verbose: log.write(" -Converting to reverse complement : EA and NEA...") 
            reverse_complement_nea = sumstats.loc[matched_index,'NEA'].apply(lambda x :get_reverse_complementary_allele(x)) 
            reverse_complement_ea = sumstats.loc[matched_index,'EA'].apply(lambda x :get_reverse_complementary_allele(x)) 
            categories = set(sumstats.loc[:,'EA'])|set(sumstats.loc[:,'NEA']) |set(reverse_complement_ea) |set(reverse_complement_nea)
            sumstats.loc[:,'EA']=pd.Categorical(sumstats.loc[:,'EA'],categories = categories) 
            sumstats.loc[:,'NEA']=pd.Categorical(sumstats.loc[:,'NEA'],categories = categories ) 
            sumstats.loc[matched_index,['NEA']] = reverse_complement_nea
            sumstats.loc[matched_index,['EA']] = reverse_complement_ea
            sumstats.loc[matched_index,status] = vchange_status(sumstats.loc[matched_index,status], 6, "4","2")
            if verbose: log.write(" -Changed the status for flipped variants : xxxxx4x -> xxxxx2x")

    ###################flip ref####################
    pattern = r"\w\w\w\w\w[35]\w"  
    #matched_index = status_match(sumstats[status],6,[3,5]) #sumstats[status].str.match(pattern)
    matched_index = sumstats[status].str[5].str.match(r"3|5")
    if sum(matched_index)>0:
        if verbose: log.write("Start to flip allele-specific stats for SNPs with status xxxxx[35]x: alt->ea , ref->nea ... ") 
        if verbose: log.write(" -Flipping "+ str(sum(matched_index)) +" variants...") 
        if ("NEA" in sumstats.columns) and ("EA" in sumstats.columns) :
            if verbose: log.write(" -Swapping column: NEA <=> EA...") 
            sumstats.loc[matched_index,['NEA','EA']] = sumstats.loc[matched_index,['EA','NEA']].values
        if "BETA" in sumstats.columns:
            if verbose: log.write(" -Flipping column: BETA = - BETA...") 
            sumstats.loc[matched_index,"BETA"] =     - sumstats.loc[matched_index,"BETA"].values
        if "BETA_95L" in sumstats.columns:
            if verbose: log.write(" -Flipping column: BETA_95L = - BETA_95L...") 
            sumstats.loc[matched_index,"BETA_95L"] =     - sumstats.loc[matched_index,"BETA_95L"].values
        if "BETA_95U" in sumstats.columns:
            if verbose: log.write(" -Flipping column: BETA_95U = - BETA_95U...") 
            sumstats.loc[matched_index,"BETA_95U"] =     - sumstats.loc[matched_index,"BETA_95U"].values
        if "EAF" in sumstats.columns:
            if verbose: log.write(" -Flipping column: EAF = 1 - EAF...") 
            sumstats.loc[matched_index,"EAF"] =   1 - sumstats.loc[matched_index,"EAF"].values
        if "OR" in sumstats.columns:
            if verbose: log.write(" -Flipping column: OR = 1 / OR...") 
            sumstats.loc[matched_index,"OR"] =   1 / sumstats.loc[matched_index,"OR"].values
        if "OR_95L" in sumstats.columns:
            if verbose: log.write(" -Flipping column: OR_95L = 1 / OR_95L...") 
            sumstats.loc[matched_index,"OR_95L"] =   1 / sumstats.loc[matched_index,"OR_95L"].values
        if "OR_95U" in sumstats.columns:
            if verbose: log.write(" -Flipping column: OR_95U = 1 / OR_95U...") 
            sumstats.loc[matched_index,"OR_95U"] =   1 / sumstats.loc[matched_index,"OR_95U"].values
        if "HR" in sumstats.columns:
            if verbose: log.write(" -Flipping column: HR = 1 / HR...") 
            sumstats.loc[matched_index,"HR"] =   1 / sumstats.loc[matched_index,"HR"].values
        if "HR_95L" in sumstats.columns:
            if verbose: log.write(" -Flipping column: HR_95L = 1 / HR_95L...") 
            sumstats.loc[matched_index,"HR_95L"] =   1 / sumstats.loc[matched_index,"HR_95L"].values
        if "HR_95U" in sumstats.columns:
            if verbose: log.write(" -Flipping column: HR_95U = 1 / HR_95U...") 
            sumstats.loc[matched_index,"HR_95U"] =   1 / sumstats.loc[matched_index,"HR_95U"].values
        if "DIRECTION" in sumstats.columns:
            if verbose: log.write(" -Flipping column: DIRECTION +-? <=> -+? ...") 
            sumstats.loc[matched_index,"DIRECTION"] =   sumstats.loc[matched_index,"DIRECTION"].apply(flip_direction)
        #change status    
        if verbose: log.write(" -Changed the status for flipped variants : xxxxx[35]x -> xxxxx[12]x") 
        sumstats.loc[matched_index,status] = vchange_status(sumstats.loc[matched_index,status], 6, "35","12")
        
    ###################flip ref for undistingushable indels####################
    pattern = r"\w\w\w\w[123][67]6"  
    #matched_index = status_match(sumstats[status],6,[1,2,3])|status_match(sumstats[status],6,[6,7])|status_match(sumstats[status],7,6) #sumstats[status].str.match(pattern)
    matched_index = sumstats[status].str[4:].str.match(r"[123][67]6")
    if sum(matched_index)>0:
        if verbose: log.write("Start to flip allele-specific stats for standardized indels with status xxxx[123][67][6]: alt->ea , ref->nea ... ") 
        if verbose: log.write(" -Flipping "+ str(sum(matched_index)) +" variants...") 
        if ("NEA" in sumstats.columns) and ("EA" in sumstats.columns) :
            if verbose: log.write(" -Swapping column: NEA <=> EA...") 
            sumstats.loc[matched_index,['NEA','EA']] = sumstats.loc[matched_index,['EA','NEA']].values
        if "BETA" in sumstats.columns:
            if verbose: log.write(" -Flipping column: BETA = - BETA...") 
            sumstats.loc[matched_index,"BETA"] =     - sumstats.loc[matched_index,"BETA"].values
        if "BETA_95L" in sumstats.columns:
            if verbose: log.write(" -Flipping column: BETA_95L = - BETA_95L...") 
            sumstats.loc[matched_index,"BETA_95L"] =     - sumstats.loc[matched_index,"BETA_95L"].values
        if "BETA_95U" in sumstats.columns:
            if verbose: log.write(" -Flipping column: BETA_95U = - BETA_95U...") 
            sumstats.loc[matched_index,"BETA_95U"] =     - sumstats.loc[matched_index,"BETA_95U"].values
        if "EAF" in sumstats.columns:
            if verbose: log.write(" -Flipping column: EAF = 1 - EAF...") 
            sumstats.loc[matched_index,"EAF"] =   1 - sumstats.loc[matched_index,"EAF"].values
        if "OR" in sumstats.columns:
            if verbose: log.write(" -Flipping column: OR = 1 / OR...") 
            sumstats.loc[matched_index,"OR"] =   1 / sumstats.loc[matched_index,"freq"].values
        if "OR_95L" in sumstats.columns:
            if verbose: log.write(" -Flipping column: OR_95L = 1 / OR_95L...") 
            sumstats.loc[matched_index,"OR_95L"] =   1 / sumstats.loc[matched_index,"OR_95L"].values
        if "OR_95U" in sumstats.columns:
            if verbose: log.write(" -Flipping column: OR_95U = 1 / OR_95U...") 
            sumstats.loc[matched_index,"OR_95U"] =   1 / sumstats.loc[matched_index,"OR_95U"].values
        if "HR" in sumstats.columns:
            if verbose: log.write(" -Flipping column: HR = 1 / HR...") 
            sumstats.loc[matched_index,"HR"] =   1 / sumstats.loc[matched_index,"freq"].values
        if "HR_95L" in sumstats.columns:
            if verbose: log.write(" -Flipping column: HR_95L = 1 / HR_95L...") 
            sumstats.loc[matched_index,"HR_95L"] =   1 / sumstats.loc[matched_index,"HR_95L"].values
        if "HR_95U" in sumstats.columns:
            if verbose: log.write(" -Flipping column: HR_95U = 1 / HR_95U...") 
            sumstats.loc[matched_index,"HR_95U"] =   1 / sumstats.loc[matched_index,"HR_95U"].values
        if "DIRECTION" in sumstats.columns:
            if verbose: log.write(" -Flipping column: DIRECTION +-? <=> -+? ...") 
            sumstats.loc[matched_index,"DIRECTION"] =   sumstats.loc[matched_index,"DIRECTION"].apply(flip_direction)
        #change status    
        if verbose: log.write(" -Changed the status for flipped variants xxxx[123][67]6 -> xxxx[123][67]4") 
        sumstats.loc[matched_index,status] = vchange_status(sumstats.loc[matched_index,status], 7, "6","4")
         # flip ref
    ###################flip statistics for reverse strand panlindromic variants####################
    pattern = r"\w\w\w\w\w[012]5"  
    #matched_index = status_match(sumstats[status],6,[0,1,2]) | status_match(sumstats[status],7,[5])#sumstats[status].str.match(pattern)
    matched_index = sumstats[status].str[5:].str.match(r"05|15|25")
    if sum(matched_index)>0:
        if verbose: log.write("Start to flip allele-specific stats for palindromic SNPs with status xxxxx[12]5: (-)strand <=> (+)strand ... ") 
        if verbose: log.write(" -Flipping "+ str(sum(matched_index)) +" variants...") 
        if "BETA" in sumstats.columns:
            if verbose: log.write(" -Flipping column: BETA = - BETA...") 
            sumstats.loc[matched_index,"BETA"] =     - sumstats.loc[matched_index,"BETA"].values
        if "BETA_95L" in sumstats.columns:
            if verbose: log.write(" -Flipping column: BETA_95L = - BETA_95L...") 
            sumstats.loc[matched_index,"BETA_95L"] =     - sumstats.loc[matched_index,"BETA_95L"].values
        if "BETA_95U" in sumstats.columns:
            if verbose: log.write(" -Flipping column: BETA_95U = - BETA_95U...") 
            sumstats.loc[matched_index,"BETA_95U"] =     - sumstats.loc[matched_index,"BETA_95U"].values
        if "EAF" in sumstats.columns:
            if verbose: log.write(" -Flipping column: EAF = 1 - EAF...") 
            sumstats.loc[matched_index,"EAF"] =   1 - sumstats.loc[matched_index,"EAF"].values
        if "OR" in sumstats.columns:
            if verbose: log.write(" -Flipping column: OR = 1 / OR...") 
            sumstats.loc[matched_index,"OR"] =   1 / sumstats.loc[matched_index,"freq"].values
        if "OR_95L" in sumstats.columns:
            if verbose: log.write(" -Flipping column: OR_95L = 1 / OR_95L...") 
            sumstats.loc[matched_index,"OR_95L"] =   1 / sumstats.loc[matched_index,"OR_95L"].values
        if "OR_95U" in sumstats.columns:
            if verbose: log.write(" -Flipping column: OR_95U = 1 / OR_95U...") 
            sumstats.loc[matched_index,"OR_95U"] =   1 / sumstats.loc[matched_index,"OR_95U"].values
        if "HR" in sumstats.columns:
            if verbose: log.write(" -Flipping column: HR = 1 / HR...") 
            sumstats.loc[matched_index,"HR"] =   1 / sumstats.loc[matched_index,"freq"].values
        if "HR_95L" in sumstats.columns:
            if verbose: log.write(" -Flipping column: HR_95L = 1 / HR_95L...") 
            sumstats.loc[matched_index,"HR_95L"] =   1 / sumstats.loc[matched_index,"HR_95L"].values
        if "HR_95U" in sumstats.columns:
            if verbose: log.write(" -Flipping column: HR_95U = 1 / HR_95U...") 
            sumstats.loc[matched_index,"HR_95U"] =   1 / sumstats.loc[matched_index,"HR_95U"].values
        if "DIRECTION" in sumstats.columns:
            if verbose: log.write(" -Flipping column: DIRECTION +-? <=> -+? ...") 
            sumstats.loc[matched_index,"DIRECTION"] =   sumstats.loc[matched_index,"DIRECTION"].apply(flip_direction)
        #change status    
        if verbose: log.write(" -Changed the status for flipped variants:  xxxxx[012]5: ->  xxxxx[012]2") 
        sumstats.loc[matched_index,status] = vchange_status(sumstats.loc[matched_index,status], 7, "5","2")
    if verbose: log.write("Finished converting successfully!")
    return sumstats
""


###############################################################################################################
# 20220426
def liftover_snv(row,chrom,converter,to_build):
    status_pre=""
    status_end=row[1][2]+"9"+row[1][4]+"99"  
    pos_0_based = int(row[0]) - 1
    results = converter[chrom][pos_0_based]
    if converter[chrom][pos_0_based]:
        # return chrom, pos_1_based
        if results[0][0].strip("chr")!=chrom:
            return pd.NA,pd.NA,"97"+status_end
        else:
            return results[0][0].strip("chr"),results[0][1]+1,to_build+status_end
    else:
        return pd.NA,pd.NA,"97"+status_end

def liftover_variant(sumstats, 
             chrom="CHR", 
             pos="POS", 
             status="STATUS",
             from_build="19", 
             to_build="38"):
    converter = get_lifter("hg"+from_build,"hg"+to_build)
    dic= get_number_to_chr(in_chr=False,xymt=["X","Y","M"])
    dic2= get_chr_to_number(out_chr=False)
    for i in sumstats[chrom].unique():
        chrom_to_convert = dic[i]
        variants_on_chrom_to_convert = sumstats[chrom]==i
        lifted = sumstats.loc[variants_on_chrom_to_convert,[pos,status]].apply(lambda x: liftover_snv(x[[pos,status]],chrom_to_convert,converter,to_build),axis=1)
        sumstats.loc[variants_on_chrom_to_convert,pos]     =   lifted.str[1]
        sumstats.loc[variants_on_chrom_to_convert,status]   =  lifted.str[2]
        sumstats.loc[variants_on_chrom_to_convert,chrom]    =  lifted.str[0].map(dic2).astype("Int64")
    return sumstats

def parallelizeliftovervariant(sumstats,n_cores=1,chrom="CHR", pos="POS", from_build="19", to_build="38",status="STATUS",remove=True, verbose=True,log=Log()):
    if check_col(sumstats,chrom,pos,status) is not True:
        if verbose: log.write("WARNING:.liftover(): specified columns not detected..skipping...")
        return sumstats
    if verbose: log.write("Start to perform liftover...")
    if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns))   
    if verbose: log.write(" -CPU Cores to use :",n_cores)
    if verbose: log.write(" -Performing liftover ...")
    if verbose: log.write(" -Creating converter : hg" + from_build +" to hg"+ to_build)
    # valid chr and pos
    pattern = r"\w\w\w0\w\w\w"  
    to_lift = sumstats[status].str.match(pattern)
    sumstats = sumstats.loc[to_lift,:].copy()
    if verbose: log.write(" -Converting variants with status code xxx0xxx :"+str(len(sumstats))+"...")
    ###########################################################################
    if sum(to_lift)>0:
        if sum(to_lift)<10000:
            n_cores=1
    
        df_split = np.array_split(sumstats.loc[:,[chrom,pos,status]], n_cores)
        pool = Pool(n_cores)
        #df = pd.concat(pool.starmap(func, df_split))
        func=liftover_variant
        sumstats.loc[:,[chrom,pos,status]] = pd.concat(pool.map(partial(func,chrom=chrom,pos=pos,from_build=from_build,to_build=to_build,status=status),df_split))
        pool.close()
        pool.join()
    ############################################################################
   
    unmap_num = len(sumstats.loc[sumstats[pos].isna(),:])    
    
    if remove is True:
        if verbose: log.write(" -Removed unmapped variants: "+str(unmap_num))
        sumstats = sumstats.loc[~sumstats[pos].isna(),:]
    
    # after liftover check chr and pos
    sumstats = fixchr(sumstats,chrom=chrom,add_prefix="",remove=remove, verbose=True)
    sumstats = fixpos(sumstats,pos=pos,remove=remove, verbose=True)
    
    if verbose: log.write("Finished liftover successfully!")
    return sumstats

###############################################################################################################
# 20220426
def sortcoordinate(sumstats,chrom="CHR",pos="POS",reindex=True,verbose=True,log=Log()):
    if check_col(sumstats,chrom,pos) is not True:
        if verbose: log.write(".liftover(): specified columns not detected..skipping...")
        return sumstats
    
    if verbose: log.write("Start to sort the genome coordinates...")
    if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns))   
    
    try:
        if sumstats[pos].dtype == "Int64":
            pass
        else:
            if verbose: log.write(" -Force converting POS to Int64...")
            sumstats[pos]  = np.floor(pd.to_numeric(sumstats[pos], errors='coerce')).astype('Int64')
    except:
        pass

    if verbose: log.write(" -Sorting genome coordinates...")
    sumstats = sumstats.sort_values(by=[chrom,pos],ascending=True,ignore_index=True)
    if verbose: log.write("Finished sorting genome coordinates successfully!")
    gc.collect()
    return sumstats
###############################################################################################################
# 20230430 added HR HR_95 BETA_95 N_CASE N_CONTROL
def sortcolumn(sumstats,verbose=True,log=Log(),order = [
        "SNPID","rsID", "CHR", "POS", "EA", "NEA", "EAF", "MAF", "BETA", "SE","BETA_95L","BETA_95U", "Z",
        "CHISQ", "P", "MLOG10P", "OR", "OR_95L", "OR_95U","HR", "HR_95L", "HR_95U","INFO", "N","N_CASE","N_CONTROL","DIRECTION","I2","P_HET","DOF","SNPR2","STATUS"
           ]):
    if verbose: log.write("Start to reorder the columns...")
    if verbose: log.write(" -Current Dataframe shape :",len(sumstats)," x ", len(sumstats.columns))   
    
    output_columns = []
    for i in order:
        if i in sumstats.columns: output_columns.append(i)
    for i in sumstats.columns:
        if i not in order: output_columns.append(i)
    if verbose: log.write(" -Reordering columns to    :", ",".join(output_columns))
    sumstats = sumstats.loc[:, output_columns]
    if verbose: log.write("Finished sorting columns successfully!")
    return sumstats

def check_col(df,*args):
    not_in_df=[]
    for i in args:
        if type(i) is str:
            if i in df.columns:
                continue
            else:
                not_in_df.append(i)
        else:
            count=0
            for j in i:
                if j in df.columns:
                    count+=1
            if count==0:
                return False
                print(" -Specified columns names was not detected. Please check:"+",".join(i))
    
    if len(not_in_df)>0:
        return False
        print(" -Specified columns names was not detected. Please check:"+",".join(not_in_df))
    return True