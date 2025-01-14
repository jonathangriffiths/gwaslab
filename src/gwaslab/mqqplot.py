import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as patches
import seaborn as sns
import numpy as np
import scipy as sp
from math import ceil
from shutil import which
from gwaslab.Log import Log
from gwaslab.calculate_gc import lambdaGC
from gwaslab.getsig import getsig
from gwaslab.getsig import annogene
from gwaslab.CommonData import get_chr_to_number
from gwaslab.CommonData import get_number_to_chr
from gwaslab.CommonData import get_recombination_rate
from gwaslab.CommonData import get_gtf
from pyensembl import EnsemblRelease
from allel import GenotypeArray
from allel import read_vcf
from allel import rogers_huff_r_between
import matplotlib as mpl
from scipy import stats
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from mpl_toolkits.axes_grid1.inset_locator import mark_inset
from matplotlib.ticker import MaxNLocator
import gc as garbage_collect
from adjustText import adjust_text
from gwaslab.textreposition import adjust_text_position
from gwaslab.annotateplot import annotate_single
from gwaslab.qqplot import _plot_qq
from gwaslab.retrievedata import auto_check_vcf_chr_dict
from gwaslab.regionalplot import _plot_regional
from gwaslab.regionalplot import process_vcf
from gwaslab.quickfix import _get_largenumber
from gwaslab.quickfix import _quick_fix_p_value
from gwaslab.quickfix import _quick_fix_pos
from gwaslab.quickfix import _quick_fix_chr
from gwaslab.quickfix import _quick_fix_eaf
from gwaslab.quickfix import _quick_fix_mlog10p
from gwaslab.quickfix import _quick_add_tchrpos
from gwaslab.quickfix import _quick_merge_sumstats
from gwaslab.quickfix import _quick_assign_i
from gwaslab.quickfix import _quick_assign_i_with_rank
from gwaslab.quickfix import _quick_extract_snp_in_region
from gwaslab.quickfix import _quick_assign_highlight_hue_pair
from gwaslab.quickfix import _quick_assign_marker_relative_size
from gwaslab.quickfix import _cut
from gwaslab.quickfix import _set_yticklabels
from gwaslab.quickfix import _jagged_y
from gwaslab.figuresave import save_figure
# 20230202 ######################################################################################################

def mqqplot(insumstats,            
          chrom=None,
          pos=None,
          p=None,
          snpid=None,
          eaf=None,
          ea="EA",
          nea="NEA",
          chr_dict = None,
          xtick_chr_dict = None,
          vcf_path=None,
          vcf_chr_dict = None,
          gtf_path="default",
          gtf_chr_dict = None,
          gtf_gene_name=None,
          rr_path="default",
          rr_header_dict=None,
          rr_chr_dict = None,
          rr_lim=(0,100),
          mlog10p="MLOG10P",
          scaled=False,
          mode="mqq",
          scatter_kwargs=None,
          qq_scatter_kwargs=None,
          qq_line_color = "grey",
          # region
          region = None,
          region_ref=None,
          region_ref2=None,
          region_step = 21,
          region_grid = False,
          region_grid_line = None,
          region_lead_grid = True,
          region_lead_grid_line = None,
          region_hspace=0.02,
          region_ld_threshold = None,
          region_ld_colors = None,
          region_ld_colors1 = None,
          region_ld_colors2 = None,
          region_recombination = True,
          region_protein_coding = True,
          region_flank_factor = 0.05,
          region_anno_bbox_args = None,
          taf = None,
          # track_n, track_n_offset,font_ratio,exon_ratio,text_offset
          tabix=None,
          mqqratio=3,
          bwindowsizekb = 100,
          density_color=False,
          density_range=(0,15),
          density_trange=(0,10),
          density_threshold=5,
          density_tpalette="Blues",
          density_palette="Reds",
          windowsizekb=500,
          anno=None,
          anno_set=None,
          anno_alias=None,
          anno_d=None,
          anno_args=None,
          anno_style="right",
          anno_fixed_arm_length=None,
          anno_source = "ensembl",
          anno_adjust=False,
          anno_max_iter=100,
          arm_offset=50,
          arm_scale=1,
          arm_scale_d=None,
          cut=0,
          skip=0,
          ystep=0,
          ylabels=None,
          ytick3=True,
          cutfactor=10,
          cut_line_color="#ebebeb",  
          cut_log = False,
          jagged=False,
          jagged_len=0.01,
          jagged_wid=0.01,
          sig_line=True,
          sig_level=5e-8,
          sig_level_lead=5e-8,
          sig_line_color="grey",
          suggestive_sig_line=False,
          suggestive_sig_level=5e-6,
          suggestive_sig_line_color="grey",
          additional_line = None,
          additional_line_color = None,
          sc_linewidth=2,
          highlight = None,
          highlight_color="#CB132D",
          highlight_windowkb = 500,
          highlight_anno_args = None,
          pinpoint= None,
          pinpoint_color ="red",
          stratified=False,
          maf_bins=None,
          maf_bin_colors = None,
          gc=True,
          include_chrXYMT = True,
          ylim=None,
          xpad=None,
          chrpad=0.03, 
          drop_chr_start=False,
          title =None,
          mtitle=None,
          qtitle=None,
          ylabel=None,
          xlabel=None,
          title_pad=1.08, 
          title_fontsize=13,
          fontsize = 9,
          font_family="Arial",
          anno_fontsize = 9,
          figargs= None,
          colors=None,
          marker_size=(5,20),
          use_rank=False,
          verbose=True,
          repel_force=0.03,
          build=None,
          dpi=200,
          save=None,
          saveargs=None,
          _invert=False,
          expected_min_mlog10p=0,
          log=Log()
          ):

# log.writeing meta info #######################################################################################
    if chr_dict is None:          
        chr_dict = get_chr_to_number()
    if xtick_chr_dict is None:         
        xtick_chr_dict = get_number_to_chr()

    if gtf_chr_dict is None:   
        gtf_chr_dict = get_number_to_chr()
    if rr_chr_dict is None:   
        rr_chr_dict = get_number_to_chr()
    if figargs is None:
        figargs= dict(figsize=(15,5))
    if "dpi" not in figargs.keys():
        figargs["dpi"] = dpi
    if region_anno_bbox_args is None:
        region_anno_bbox_args = dict()
    if anno_set is None:
        anno_set=list()
    if anno_alias is None:
        anno_alias=dict()
    if anno_d is None:
        anno_d=dict()
    if anno_args is None:
        anno_args=dict()
    if colors is None:
        colors=["#597FBD","#74BAD3"]
    if region_grid_line is None:
        region_grid_line = {"linewidth": 2,"linestyle":"--"}
    if region_lead_grid_line is None:
        region_lead_grid_line = {"alpha":0.5,"linewidth" : 2,"linestyle":"--","color":"#FF0000"}
    if region_ld_threshold is None:
        region_ld_threshold = [0.2,0.4,0.6,0.8]
    if region_ld_colors is None:     
        region_ld_colors = ["#E4E4E4","#020080","#86CEF9","#24FF02","#FDA400","#FF0000","#FF0000"]
    if region_ld_colors1 is None:
        region_ld_colors1 = ["#E4E4E4","#F8CFCF","#F5A2A5","#F17474","#EB4445","#E51819","#E51819"]
    if region_ld_colors2 is None:
        region_ld_colors2 = ["#E4E4E4","#D8E2F2","#AFCBE3","#86B3D4","#5D98C4","#367EB7","#367EB7"]
    if taf is None:
        taf = [4,0,0.95,1,1]
    if maf_bins is None:
        maf_bins=[(0, 0.01), (0.01, 0.05), (0.05, 0.25),(0.25,0.5)]
    if maf_bin_colors is None:
        maf_bin_colors = ["#f0ad4e","#5cb85c", "#5bc0de","#000042"]
    if saveargs is None:
        saveargs = {"dpi":300,"facecolor":"white"}
    if highlight is None:
        highlight = list()
    if highlight_anno_args is None:
        highlight_anno_args = {}
    if pinpoint is None:
        pinpoint = list()  
    if build is None:
        build = "19"
    if scatter_kwargs is None:
        scatter_kwargs={}
    if qq_scatter_kwargs is None:
        qq_scatter_kwargs={}
    
    if save is not None:
        if type(save) is not bool:
            if len(save)>3:
                if save[-3:]=="pdf" or save[-3:]=="svg":
                    figargs["dpi"]=72
                    scatter_kwargs["rasterized"]=True
                    qq_scatter_kwargs["rasterized"]=True

    if verbose: log.write("Start to plot manhattan/qq plot with the following basic settings:")
    if verbose: log.write(" -Genomic coordinates version: {}...".format(build))
    if build is None or build=="99":
        if verbose: log.write("   -WARNING!!! Genomic coordinates version is unknown...")
    if verbose: log.write(" -Genome-wide significance level is set to "+str(sig_level)+" ...")
    if verbose: log.write(" -Raw input contains "+str(len(insumstats))+" variants...")
    if verbose: log.write(" -Plot layout mode is : "+mode)
    if len(anno_set)>0 and ("m" in mode):
        if verbose: log.write(" -Variants to annotate : "+",".join(anno_set))    
    if len(highlight)>0 and ("m" in mode):
        if pd.api.types.is_list_like(highlight[0]):
            if len(highlight[0]) == len(highlight_color):
                log.write(" -WARNING: number of locus list does not match number of colors !!!")
            for i, highlight_set in enumerate(highlight):
                  if verbose: log.write(" -Set {} loci to highlight ({}) : ".format(i+1, highlight_color[i%len(highlight_color)])+",".join(highlight_set))   
            if verbose: log.write("  -Highlight_window is set to: ", highlight_windowkb, " kb") 
        else:
            if verbose: log.write(" -Loci to highlight ({}): ".format(highlight_color)+",".join(highlight))    
            if verbose: log.write("  -Highlight_window is set to: ", highlight_windowkb, " kb") 
    
    if len(pinpoint)>0 :
        if pd.api.types.is_list_like(pinpoint[0]):
            if len(pinpoint[0]) == len(pinpoint_color):
                log.write(" -WARNING: number of variant list does not match number of colors !!!")
            for i, pinpoint_set in enumerate(pinpoint):
                  if verbose: log.write(" -Set {} variants to pinpoint ({}) : ".format(i+1,pinpoint_color[i%len(pinpoint_color)])+",".join(pinpoint_set))      
        else:
            if verbose: log.write(" -Variants to pinpoint ({}) : ".format(pinpoint_color)+",".join(pinpoint))   
    
    if region is not None:
        if verbose: log.write(" -Region to plot : chr"+str(region[0])+":"+str(region[1])+"-"+str(region[2])+".")  
    
    # construct line series for coversion
    if additional_line is None:
        lines_to_plot = pd.Series([sig_level, suggestive_sig_level] )
    else:
        lines_to_plot = pd.Series([sig_level, suggestive_sig_level] + additional_line ) 
        if additional_line_color is None:
            additional_line_color = ["grey"]
    lines_to_plot = -np.log10(lines_to_plot)

    vcf_chr_dict = auto_check_vcf_chr_dict(vcf_path, vcf_chr_dict, verbose, log)
# Plotting mode selection : layout ####################################################################
    # ax1 : manhattanplot / brisbane plot
    # ax2 : qq plot 
    # ax3 : gene track
    # ax4 : recombination rate
    # ax5 : miami plot lower panel

    # "m" : Manhattan plot
    # "qq": QQ plot
    # "r" : regional plot
    
    if  mode=="qqm": 
        fig, (ax2, ax1) = plt.subplots(1, 2,gridspec_kw={'width_ratios': [1, mqqratio]},**figargs)
    elif mode=="mqq":
        fig, (ax1, ax2) = plt.subplots(1, 2,gridspec_kw={'width_ratios': [mqqratio, 1]},**figargs)
    elif mode=="m":
        fig, ax1 = plt.subplots(1, 1,**figargs)
    elif mode=="qq": 
        fig, ax2 = plt.subplots(1, 1,**figargs) 
    elif mode=="r": 
        figargs["figsize"] = (15,10)
        fig, (ax1, ax3) = plt.subplots(2, 1, sharex=True, 
                                       gridspec_kw={'height_ratios': [mqqratio, 1]},**figargs)
        plt.subplots_adjust(hspace=region_hspace)
    elif mode =="b" :
        figargs["figsize"] = (15,5)
        fig, ax1 = plt.subplots(1, 1,**figargs)
        sig_level=1,
        sig_line=False,
        windowsizekb = 100000000   
        mode="mb"
        scatter_kwargs={"marker":"s"}
        marker_size= (marker_size[1],marker_size[1])
    else:
        raise ValueError("Please select one from the 5 modes: mqq/qqm/m/qq/r/b")

# Read sumstats #################################################################################################

    usecols=[]
    #  P ###############################################################################
    if mlog10p in insumstats.columns and scaled is True:
        usecols.append(mlog10p)
    elif p in insumstats.columns:
        # p value is necessary for all modes.
        usecols.append(p)  
    elif "b" in mode:
        pass
    else :
        raise ValueError("Please make sure "+p+" column is in input sumstats.")
    
    # CHR and POS ########################################################################
    # chrom and pos exists && (m || r mode)
    if (chrom is not None) and (pos is not None) and (("qq" in mode) or ("m" in mode) or ("r" in mode)):
        # when manhattan plot, chrom and pos is needed.
        if chrom in insumstats.columns:
            usecols.append(chrom)
        else:
            raise ValueError("Please make sure "+chrom+" column is in input sumstats.")
        if pos in insumstats.columns:
            usecols.append(pos)
        else:
            raise ValueError("Please make sure "+pos+" column is in input sumstats.")
    
    # for regional plot ea and nea
    if ("r" in mode) and (ea in insumstats.columns) and (nea in insumstats.columns):
        try:
            usecols.append(ea)
            usecols.append(nea)
        except:
            raise ValueError("Please make sure {} and {} columns are in input sumstats.".format(nea,ea))
    # SNPID ###############################################################################
    if len(highlight)>0 or len(pinpoint)>0 or (snpid is not None):
        # read snpid when highlight/pinpoint is needed.
        if snpid in insumstats.columns:
            usecols.append(snpid)
        else:
            raise ValueError("Please make sure "+snpid+" column is in input sumstats.")
    
    # EAF #################################################################################
    if (stratified is True) and (eaf is not None):
        # read eaf when stratified qq plot is needed.
        if eaf in insumstats.columns:
            usecols.append(eaf)
        else:
            raise ValueError("Please make sure "+eaf+" column is in input sumstats.")
    
    # ANNOTATion ##########################################################################
    #
    if len(anno_set)>0 or len(anno_alias)>0:
        if anno is None:
            anno=True
    if (anno is not None) and (anno is not True):
        if anno=="GENENAME":
            pass
        elif (anno in insumstats.columns):
            if (anno not in usecols):
                usecols.append(anno)
        else:
            raise ValueError("Please make sure "+anno+" column is in input sumstats.")
    
    if (density_color==True) or ("b" in mode and "DENSITY" in insumstats.columns):
        usecols.append("DENSITY")

    #################################################################################################
    sumstats = insumstats.loc[:,usecols].copy()


    #Standardize
    ## Annotation
    if (anno == "GENENAME"):
        anno_sig=True
    elif (anno is not None) and (anno is not True):
        sumstats["Annotation"]=sumstats.loc[:,anno].astype("string")   
      
    ## P value
    ## m, qq, r
    if "b" not in mode:   
        if scaled is True:
            sumstats["raw_P"] = pd.to_numeric(sumstats[mlog10p], errors='coerce')
        else:
            sumstats["raw_P"] = sumstats[p].astype("float64")
    
    ## CHR & POS
    ## m, qq, b
    if "m" in mode or "r" in mode or "b" in mode: 
        # convert CHR to int
        ## CHR X,Y,MT conversion ############################
        sumstats[pos] = _quick_fix_pos(sumstats[pos])
        sumstats[chrom] = _quick_fix_chr(sumstats[chrom], chr_dict=chr_dict)

    ## r
    if region is not None:
        region_chr = region[0]
        region_start = region[1]
        region_end = region[2]
        marker_size=(25,45)
        if verbose:log.write(" -Extract SNPs in region : chr"+str(region_chr)+":"+str(region[1])+"-"+str(region[2])+ "...")
        
        in_region_snp = (sumstats[chrom]==region_chr) &(sumstats[pos]<region_end) &(sumstats[pos]>region_start)
        if verbose:log.write(" -Extract SNPs in specified regions: "+str(sum(in_region_snp)))
        sumstats = sumstats.loc[in_region_snp,:]
        if len(sumstats)==0:
            log.write(" -Warning : No valid data! Please check the input.")
            return None
    
    ## EAF
    eaf_raw = pd.Series(dtype="float64")
    if stratified is True: 
        sumstats["MAF"] = _quick_fix_eaf(sumstats[eaf])
        # for stratified qq plot
        eaf_raw = sumstats["MAF"].copy()
        
    if len(highlight)>0 and ("m" in mode):
        sumstats["HUE"] = pd.NA
        sumstats["HUE"] = sumstats["HUE"].astype("Int64")

    if verbose: log.write("Finished loading specified columns from the sumstats.")


#sanity check############################################################################################################
    if verbose: log.write("Start conversion and sanity check:")
    
    if ("m" in mode or "r" in mode): 
        pre_number=len(sumstats)
        #sanity check : drop variants with na values in chr and pos df
        sumstats = sumstats.dropna(subset=[chrom,pos])
        after_number=len(sumstats)
        if verbose:log.write(" -Removed "+ str(pre_number-after_number) +" variants with nan in CHR or POS column ...")
        out_of_range_chr = sumstats[chrom]<=0
        if verbose:log.write(" -Removed {} varaints with CHR <=0...".format(sum(out_of_range_chr)))
        sumstats = sumstats.loc[~out_of_range_chr,:]
    
    if stratified is True: 
        pre_number=len(sumstats)
        sumstats = sumstats.dropna(subset=["MAF"])
        after_number=len(sumstats)
        if verbose:log.write(" -Removed "+ str(pre_number-after_number) +" variants with nan in EAF column ...")
            
        ## Highlight
    if len(highlight)>0 and ("m" in mode or "r" in mode):
        if pd.api.types.is_list_like(highlight[0]):
            for i, highlight_set in enumerate(highlight):
                to_highlight = sumstats.loc[sumstats[snpid].isin(highlight_set),:]
                #assign colors: 0 is hightlight color
                for index,row in to_highlight.iterrows():
                    target_chr = int(row[chrom])
                    target_pos = int(row[pos])
                    right_chr=sumstats[chrom]==target_chr
                    up_pos=sumstats[pos]>target_pos-highlight_windowkb*1000
                    low_pos=sumstats[pos]<target_pos+highlight_windowkb*1000
                    sumstats.loc[right_chr&up_pos&low_pos,"HUE"]=i
        else:
            to_highlight = sumstats.loc[sumstats[snpid].isin(highlight),:]
            #assign colors: 0 is hightlight color
            for index,row in to_highlight.iterrows():
                target_chr = int(row[chrom])
                target_pos = int(row[pos])
                right_chr=sumstats[chrom]==target_chr
                up_pos=sumstats[pos]>target_pos-highlight_windowkb*1000
                low_pos=sumstats[pos]<target_pos+highlight_windowkb*1000
                sumstats.loc[right_chr&up_pos&low_pos,"HUE"]=0

# Density #####################################################################################################              
    if "b" in mode and "DENSITY" not in sumstats.columns:
        if verbose:log.write(" -Calculating DENSITY with windowsize of ",bwindowsizekb ," kb")
        large_number = _get_largenumber(sumstats[pos].max(),log=log)

        stack=[]
        sumstats["TCHR+POS"] = sumstats[chrom]*large_number +  sumstats[pos]
        sumstats = sumstats.sort_values(by="TCHR+POS")
        for index,row in sumstats.iterrows():
            stack.append([row["SNPID"],row["TCHR+POS"],0])  
            for i in range(2,len(stack)+1):
                if stack[-i][1]>= (row["TCHR+POS"]- 1000*bwindowsizekb):
                    stack[-i][2]+=1
                    stack[-1][2]+=1
                else:
                    break
        df = pd.DataFrame(stack,columns=["SNPID","TCHR+POS","DENSITY"])
        sumstats["DENSITY"] = df["DENSITY"].values
        bmean=sumstats["DENSITY"].mean()
        bmedian=sumstats["DENSITY"].median()
    elif "b" in mode and "DENSITY" in sumstats.columns:
        bmean=sumstats["DENSITY"].mean()
        bmedian=sumstats["DENSITY"].median()
        if verbose:log.write(" -DENSITY column exists. Skipping calculation...")
     
    #############################
# P value conversion #####################################################################################################  
    ## m,qq,r -> dropna
    if "b" not in mode:
        pre_number=len(sumstats)
        sumstats = sumstats.dropna(subset=["raw_P"])
        after_number=len(sumstats)
        if verbose:log.write(" -Removed "+ str(pre_number-after_number) +" variants with nan in P column ...")
    
    ## b: value to plot is density
    if "b" in mode:
        sumstats["scaled_P"] = sumstats["DENSITY"].copy()
        sumstats["raw_P"] = -np.log10(sumstats["DENSITY"].copy()+2)
    elif scaled is True:
        if verbose:log.write(" -P values are already converted to -log10(P)!")
        sumstats["scaled_P"] = sumstats["raw_P"].copy()
        sumstats["raw_P"] = np.power(10,-sumstats["scaled_P"].astype("float64"))
    else:
        if not scaled:
            # quick fix p
            sumstats = _quick_fix_p_value(sumstats, verbose=verbose, log=log)

        # quick fix mlog10p
        sumstats = _quick_fix_mlog10p(sumstats, scaled=scaled, verbose=verbose, log=log)

    # raw p for calculate lambda
    p_toplot_raw = sumstats[["CHR","scaled_P"]].copy()
    
    # filter out variants with -log10p < skip
    sumstats = sumstats.loc[sumstats["scaled_P"]>=skip,:]
    garbage_collect.collect()
    

    # 

    # shrink variants above cut line #########################################################################################
    try:
        sumstats["scaled_P"], maxy, maxticker, cut, cutfactor,ylabels_converted, lines_to_plot = _cut(series = sumstats["scaled_P"], 
                                                                        mode =mode, 
                                                                        cut=cut,
                                                                        skip=skip,
                                                                        cutfactor = cutfactor,
                                                                        ylabels=ylabels,
                                                                        cut_log = cut_log,
                                                                        verbose =verbose, 
                                                                        lines_to_plot=lines_to_plot,
                                                                        log = log)
    except:
        log.write(" -Warning : No valid data! Please check the input.")
        return None
    
    # Manhattan plot ##########################################################################################################
    ## regional plot ->rsq
        #calculate rsq]
    if vcf_path is not None:
        if tabix is None:
            tabix = which("tabix")
        sumstats = process_vcf(sumstats=sumstats, 
                               vcf_path=vcf_path,
                               region=region, 
                               region_ref=region_ref, 
                               region_ref2=region_ref2,
                               log=log ,
                               pos=pos,
                               ea=ea,
                               nea=nea,
                               region_ld_threshold=region_ld_threshold,
                               verbose=verbose,
                               vcf_chr_dict=vcf_chr_dict,
                               tabix=tabix)

    #sort & add id
    ## Manhatann plot ###################################################
    if ("m" in mode) or ("r" in mode): 
        # assign index i and tick position
        sumstats,chrom_df=_quick_assign_i_with_rank(sumstats, chrpad=chrpad, use_rank=use_rank, chrom="CHR",pos="POS",drop_chr_start=drop_chr_start)
        
        ## Assign marker size ##############################################
        sumstats["s"]=1
        if "b" not in mode:
            sumstats.loc[sumstats["scaled_P"]>-np.log10(5e-4),"s"]=2
            sumstats.loc[sumstats["scaled_P"]>-np.log10(suggestive_sig_level),"s"]=3
            sumstats.loc[sumstats["scaled_P"]>-np.log10(sig_level),"s"]=4
        sumstats["chr_hue"]=sumstats[chrom].astype("string")

        if vcf_path is not None:
            sumstats["chr_hue"]=sumstats["LD"]

        if verbose:log.write("Start to create manhattan plot with "+str(len(sumstats))+" variants:")
        ## default seetings
        
        palette = sns.color_palette(colors,n_colors=sumstats[chrom].nunique())  
        

        legend = None
        style=None
        linewidth=0
        edgecolor="black"
        # if regional plot assign colors
        if vcf_path is not None:
            legend=None
            linewidth=1
            palette = { i:region_ld_colors[i] for i in range(len(region_ld_colors))}
            if region_ref2 is not None:
                palette = {} 
                for i in range(len(region_ld_colors)):
                    palette[i]=region_ld_colors1[i]
                    palette[100+i]=region_ld_colors2[i]
                edgecolor="none"
                scatter_kwargs["markers"]=['o', 's']
                style="SHAPE"
                
            
            
        ## if highlight 
        highlight_i = pd.DataFrame()
        if len(highlight) >0:
            plot = sns.scatterplot(data=sumstats, x='i', y='scaled_P',
                               hue='chr_hue',
                               palette=palette,
                               legend=legend,
                               style=style,
                               size="s",
                               sizes=marker_size,
                               linewidth=linewidth,
                               zorder=2,ax=ax1,edgecolor=edgecolor, **scatter_kwargs)   
            if pd.api.types.is_list_like(highlight[0]):
                for i, highlight_set in enumerate(highlight):
                    if verbose: log.write(" -Highlighting set {} target loci...".format(i+1))
                    print(sumstats["HUE"].dtype)
                    sns.scatterplot(data=sumstats.loc[sumstats["HUE"]==i], x='i', y='scaled_P',
                        hue="HUE",
                        palette={i:highlight_color[i%len(highlight_color)]},
                        legend=legend,
                        style=style,
                        size="s",
                        sizes=(marker_size[0]+1,marker_size[1]+1),
                        linewidth=linewidth,
                        zorder=3+i,ax=ax1,edgecolor=edgecolor,**scatter_kwargs)  
                highlight_i = sumstats.loc[~sumstats["HUE"].isna(),"i"].values
            else:
                if verbose: log.write(" -Highlighting target loci...")
                sns.scatterplot(data=sumstats.loc[sumstats["HUE"]==0], x='i', y='scaled_P',
                    hue="HUE",
                    palette={0:highlight_color},
                    legend=legend,
                    style=style,
                    size="s",
                    sizes=(marker_size[0]+1,marker_size[1]+1),
                    linewidth=linewidth,
                    zorder=3,ax=ax1,edgecolor=edgecolor,**scatter_kwargs)  
                # for annotate
                highlight_i = sumstats.loc[sumstats[snpid].isin(highlight),"i"].values
        
        ## if not highlight    
        else:
            if density_color == True:
                hue = "DENSITY_hue"
                s = "DENSITY"
                to_plot = sumstats.sort_values("DENSITY")
                to_plot["DENSITY_hue"] = to_plot["DENSITY"].astype("float")
                plot = sns.scatterplot(data=to_plot.loc[to_plot["DENSITY"]<=density_threshold,:], x='i', y='scaled_P',
                       hue=hue,
                       palette= density_tpalette,
                       legend=legend,
                       style=style,
                       size=s,
                       sizes=(marker_size[0]+1,marker_size[0]+1),
                       linewidth=linewidth,
                       hue_norm=density_trange,
                       zorder=2,ax=ax1,edgecolor=edgecolor,**scatter_kwargs) 

                plot = sns.scatterplot(data=to_plot.loc[to_plot["DENSITY"]>density_threshold,:], x='i', y='scaled_P',
                   hue=hue,
                   palette= density_palette,
                   legend=legend,
                   style=style,
                   size=s,
                   sizes=marker_size,
                   hue_norm=density_range,
                   linewidth=linewidth,
                   zorder=2,ax=ax1,edgecolor=edgecolor,**scatter_kwargs)   
            else:
                s = "s"
                hue = 'chr_hue'
                hue_norm=None
                to_plot = sumstats
                plot = sns.scatterplot(data=to_plot, x='i', y='scaled_P',
                       hue=hue,
                       palette= palette,
                       legend=legend,
                       style=style,
                       size=s,
                       sizes=marker_size,
                       hue_norm=hue_norm,
                       linewidth=linewidth,
                       edgecolor = edgecolor,
                       zorder=2,ax=ax1,**scatter_kwargs)   
        
        
        ## if pinpoint variants
        if (len(pinpoint)>0):
            if pd.api.types.is_list_like(pinpoint[0]):
                for i, pinpoint_set in enumerate(pinpoint):
                    if sum(sumstats[snpid].isin(pinpoint_set))>0:
                        to_pinpoint = sumstats.loc[sumstats[snpid].isin(pinpoint_set),:]
                        if verbose: log.write(" -Pinpointing set {} target vairants...".format(i+1))
                        ax1.scatter(to_pinpoint["i"],to_pinpoint["scaled_P"],color=pinpoint_color[i%len(pinpoint_color)],zorder=100,s=marker_size[1]+1)
                    else:
                        if verbose: log.write(" -Target vairants to pinpoint were not found. Skip pinpointing process...")
            else:
                if sum(sumstats[snpid].isin(pinpoint))>0:
                    to_pinpoint = sumstats.loc[sumstats[snpid].isin(pinpoint),:]
                    if verbose: log.write(" -Pinpointing target vairants...")
                    ax1.scatter(to_pinpoint["i"],to_pinpoint["scaled_P"],color=pinpoint_color,zorder=100,s=marker_size[1]+1)
                else:
                    if verbose: log.write(" -Target vairants to pinpoint were not found. Skip pinpointing process...")
            

        
        #ax1.set_xticks(chrom_df.astype("float64"))
        #ax1.set_xticklabels(chrom_df.index.astype("Int64").map(xtick_chr_dict),fontsize=fontsize,family=font_family)
        
        # if regional plot : pinpoint lead , add color bar ##################################################
        if (region is not None) and ("r" in mode):
            ax1, ax3 =_plot_regional(
                                sumstats=sumstats,
                                fig=fig,
                                ax1=ax1,
                                ax3=ax3,
                                region=region,
                                vcf_path=vcf_path,
                                marker_size=marker_size,
                                fontsize=fontsize,
                                build=build,
                                chrom_df=chrom_df,
                                xtick_chr_dict=xtick_chr_dict,
                                cut_line_color=cut_line_color,
                                vcf_chr_dict =vcf_chr_dict,
                                gtf_path=gtf_path,
                                gtf_chr_dict = gtf_chr_dict,
                                gtf_gene_name=gtf_gene_name,
                                rr_path=rr_path,
                                rr_header_dict=rr_header_dict,
                                rr_chr_dict = rr_chr_dict,
                                rr_lim=rr_lim,
                                mode=mode,
                                region_step = region_step,
                                region_ref=region_ref,
                                region_ref2=region_ref2,
                                region_grid = region_grid,
                                region_grid_line = region_grid_line,
                                region_lead_grid = region_lead_grid,
                                region_lead_grid_line = region_lead_grid_line,
                                region_hspace=region_hspace,
                                region_ld_threshold = region_ld_threshold,
                                region_ld_colors = region_ld_colors,
                                region_ld_colors1=region_ld_colors1,
                                region_ld_colors2=region_ld_colors2,
                                region_recombination = region_recombination,
                                region_protein_coding=region_protein_coding,
                                region_flank_factor =region_flank_factor,
                                taf=taf,
                                tabix=tabix,
                                chrom=chrom,
                                pos=pos,
                                verbose=verbose,
                                log=log
                            )

        if region is None:
            #plot.set_xlabel(chrom)
            ax1.set_xticks(chrom_df.astype("float64"))
            ax1.set_xticklabels(chrom_df.index.astype("Int64").map(xtick_chr_dict),fontsize=fontsize,family=font_family)
        
        # genomewide significant line
        if sig_line is True:
            sigline = ax1.axhline(y=lines_to_plot[0], 
                                  linewidth = sc_linewidth,
                                  linestyle="--",
                                  color=sig_line_color,
                                  zorder=1)
        if suggestive_sig_line is True:
            suggestive_sig_line = ax1.axhline(y=lines_to_plot[1], 
                                              linewidth = sc_linewidth, 
                                              linestyle="--", 
                                              color=suggestive_sig_line_color,
                                              zorder=1)
        if additional_line is not None:
            for index, level in enumerate(lines_to_plot[2:].values):
                ax1.axhline(y=level, 
                            linewidth = sc_linewidth, 
                            linestyle="--", 
                            color=additional_line_color[index%len(additional_line_color)],
                            zorder=1)
            
            
        # for brisbane plot, add median and mean line
        if "b" in mode:    
            meanline = ax1.axhline(y=bmean, linewidth = sc_linewidth,linestyle="-",color=sig_line_color,zorder=1000)
            medianline = ax1.axhline(y=bmedian, linewidth = sc_linewidth,linestyle="--",color=sig_line_color,zorder=1000)
        
        ax1 = _set_yticklabels(cut=cut,
                     cutfactor=cutfactor,
                     cut_log=cut_log,
                     ax1=ax1,
                     skip=skip,
                     maxy=maxy,
                     maxticker=maxticker,
                     ystep=ystep,
                     sc_linewidth=sc_linewidth,
                     cut_line_color=cut_line_color,
                     fontsize=fontsize,
                     font_family=font_family,
                     ytick3=ytick3,
                     ylabels=ylabels,
                     ylabels_converted=ylabels_converted
                     )

        # Get top variants for annotation #######################################################
        if (anno and anno!=True) or (len(anno_set)>0):
            if len(anno_set)>0:
                to_annotate=sumstats.loc[sumstats[snpid].isin(anno_set),:]
                if to_annotate.empty is not True:
                    if verbose: log.write(" -Found "+str(len(to_annotate))+" specified variants to annotate...")
            else:
                to_annotate=getsig(sumstats.loc[sumstats["scaled_P"]> float(-np.log10(sig_level_lead)),:],
                               snpid,
                               chrom,
                               pos,
                               "raw_P",
                               sig_level=sig_level_lead,
                               windowsizekb=windowsizekb,
                               scaled=scaled,
                               mlog10p="scaled_P",
                               verbose=False)
                if (to_annotate.empty is not True) and ("b" not in mode):
                    if verbose: log.write(" -Found "+str(len(to_annotate))+" significant variants with a sliding window size of "+str(windowsizekb)+" kb...")
        else:
            to_annotate=getsig(sumstats.loc[sumstats["scaled_P"]> float(-np.log10(sig_level_lead)),:],
                               "i",
                               chrom,
                               pos,
                               "raw_P",
                               windowsizekb=windowsizekb,
                               scaled=scaled,
                               verbose=False,
                               mlog10p="scaled_P",
                               sig_level=sig_level_lead)
            if (to_annotate.empty is not True) and ("b" not in mode):
                if verbose: log.write(" -Found "+str(len(to_annotate))+" significant variants with a sliding window size of "+str(windowsizekb)+" kb...")
        if (to_annotate.empty is not True) and anno=="GENENAME":
            to_annotate = annogene(to_annotate,
                                   id=snpid,
                                   chrom=chrom,
                                   pos=pos,
                                   log=log,
                                   build=build,
                                   source=anno_source,
                                   verbose=verbose).rename(columns={"GENE":"Annotation"})

        # Add Annotation to manhattan plot #######################################################
        
        if "b" in mode:
            if ylabel is None:
                ylabel ="Density of GWAS \n SNPs within "+str(bwindowsizekb)+" kb"
            ax1.set_ylabel(ylabel,ha="center",va="bottom",fontsize=fontsize,family=font_family)
        else:
            if ylabel is None:
                ylabel ="$-log_{10}(P)$"
            ax1.set_ylabel(ylabel,fontsize=fontsize,family=font_family)

        if region is not None:
            if xlabel is None:
                xlabel = "Chromosome "+str(region[0])+" (MB)"
            if (gtf_path is not None ) and ("r" in mode):
                ax3.set_xlabel(xlabel,fontsize=fontsize,family=font_family)
            else:
                ax1.set_xlabel(xlabel,fontsize=fontsize,family=font_family)
        else:
            if xlabel is None:
                xlabel = "Chromosome"
            ax1.set_xlabel(xlabel,fontsize=fontsize,family=font_family)
        ##
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)
        ax1.spines["left"].set_visible(True)
        if mode=="r":
            ax1.spines["top"].set_visible(True)
            ax1.spines["top"].set_zorder(1)    
            ax1.spines["right"].set_visible(True)
        
        if verbose: log.write("Finished creating Manhattan plot successfully!")
        if mtitle and anno and len(to_annotate)>0: 
            pad=(ax1.transData.transform((skip, title_pad*maxy))[1]-ax1.transData.transform((skip, maxy)))[1]
            ax1.set_title(mtitle,pad=pad,fontsize=title_fontsize,family=font_family)
        elif mtitle:
            ax1.set_title(mtitle,fontsize=title_fontsize,family=font_family)
            
        # add annotation arrows and texts
        ax1 = annotate_single(
                                sumstats=sumstats,
                                anno=anno,
                                mode=mode,
                                ax1=ax1,
                                highlight_i=highlight_i,
                                highlight_anno_args=highlight_anno_args,
                                to_annotate=to_annotate,
                                anno_d=anno_d,
                                anno_alias=anno_alias,
                                anno_style=anno_style,
                                anno_args=anno_args,
                                arm_scale=arm_scale,
                                anno_max_iter=anno_max_iter,
                                arm_scale_d=arm_scale_d,
                                arm_offset=arm_offset,
                                anno_adjust=anno_adjust,
                                anno_fixed_arm_length=anno_fixed_arm_length,
                                maxy=maxy,
                                anno_fontsize= anno_fontsize,
                                font_family=font_family,
                                region=region,
                                region_anno_bbox_args=region_anno_bbox_args,
                                skip=skip,
                                snpid=snpid,
                                chrom=chrom,
                                pos=pos,
                                repel_force=repel_force,
                                verbose=verbose,
                                log=log
                            )  
    # Creating Manhatann plot Finished #####################################################################

    # QQ plot #########################################################################################################
    if "qq" in mode:
        # ax2 qqplot
        ax2 =_plot_qq(
                    sumstats=sumstats,
                    p_toplot_raw=p_toplot_raw,
                    ax2=ax2,
                    maxticker=maxticker,
                    marker_size=marker_size,
                    gc=gc,
                    cut=cut,
                    cutfactor=cutfactor,
                    cut_log=cut_log,
                    skip=skip,
                    maxy=maxy,
                    ystep=ystep,
                    colors=colors,
                    qq_line_color=qq_line_color,
                    stratified=stratified,
                    eaf_raw=eaf_raw,
                    maf_bins=maf_bins,
                    maf_bin_colors=maf_bin_colors,
                    fontsize=fontsize,
                    font_family=font_family,
                    qtitle=qtitle,
                    title_fontsize=title_fontsize,
                    include_chrXYMT=include_chrXYMT,
                    cut_line_color=cut_line_color,
                    linewidth=sc_linewidth,
                    ytick3 = ytick3,
                    ylabels = ylabels,
                    ylabels_converted = ylabels_converted,
                    verbose=verbose,
                    qq_scatter_kwargs=qq_scatter_kwargs,
                    expected_min_mlog10p=expected_min_mlog10p,
                    log=log
                )
    
    
    if xpad!=None:
        ax1.set_xlim([0 - xpad* sumstats["i"].max(),(1+xpad)*sumstats["i"].max()])
    
    if jagged==True:
        ax1 = _jagged_y(cut=cut,skip=skip,ax1=ax1,mode=1,mqqratio=mqqratio,jagged_len=jagged_len,jagged_wid=jagged_wid)
        if "qq" in mode:
            ax2 = _jagged_y(cut=cut,skip=skip,ax1=ax2,mode=2,mqqratio=mqqratio,jagged_len=jagged_len,jagged_wid=jagged_wid)
    
    if ylim is not None:
        ax1.set_ylim(ylim)
        if "qq" in mode:
            ax2.set_ylim(ylim)
    # Saving plot ##########################################################################################################
    #if save:
    #    if verbose: log.write("Saving plot:")
    #    if save==True:
    #        fig.savefig("./"+mode+"_plot.png",bbox_inches="tight",**saveargs)
    #        log.write(" -Saved to "+ "./"+mode+"_plot.png" + " successfully!" )
    #    else:
    #        fig.savefig(save,bbox_inches="tight",**saveargs)
    #        log.write(" -Saved to "+ save + " successfully!" )
    
    # add title 
    if title and anno and len(to_annotate)>0:
        # increase height if annotation 
        fig.suptitle(title , fontsize = title_fontsize ,x=0.5, y=1.05)
    else:
        fig.suptitle(title , fontsize = title_fontsize, x=0.5,y=1)

    save_figure(fig = fig, save = save, keyword=mode, saveargs=saveargs, log = log, verbose=verbose)

    garbage_collect.collect()
    
    # Return matplotlib figure object #######################################################################################
    return fig, log
