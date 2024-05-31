#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/11 19:26
@Author  : alexanderwu
@File    : design_api.py
@Modified By: mashenquan, 2023/11/27.
            1. According to Section 2.2.3.1 of RFC 135, replace file data in the message with the file name.
            2. According to the design in Section 2.2.3.5.3 of RFC 135, add incremental iteration functionality.
@Modified By: mashenquan, 2023/12/5. Move the generation logic of the project name to WritePRD.
"""
import json
import uuid
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from metagpt.actions import Action
from metagpt.actions.design_api_an import (
    DATA_STRUCTURES_AND_INTERFACES,
    DESIGN_API_NODE,
    PROGRAM_CALL_FLOW,
    REFINED_DATA_STRUCTURES_AND_INTERFACES,
    REFINED_DESIGN_NODE,
    REFINED_PROGRAM_CALL_FLOW,
)
from metagpt.const import DATA_API_DESIGN_FILE_REPO, SEQ_FLOW_FILE_REPO
from metagpt.logs import logger
from metagpt.schema import AIMessage, Document, Documents, Message
from metagpt.utils.common import aread, awrite, to_markdown_code_block
from metagpt.utils.mermaid import mermaid_to_file
from metagpt.utils.project_repo import ProjectRepo
from metagpt.utils.report import DocsReporter, GalleryReporter

NEW_REQ_TEMPLATE = """
### Legacy Content
{old_design}

### New Requirements
{context}
"""


class WriteDesign(Action):
    name: str = ""
    i_context: Optional[str] = None
    desc: str = (
        "Based on the PRD, think about the system design, and design the corresponding APIs, "
        "data structures, library tables, processes, and paths. Please provide your design, feedback "
        "clearly and in detail."
    )
    repo: Optional[ProjectRepo] = Field(default=None, exclude=True)
    input_args: Optional[BaseModel] = Field(default=None, exclude=True)

    async def run(
        self,
        with_messages: List[Message] = None,
        *,
        user_requirement: str = "",
        prd_filename: str = "",
        exists_design_filename: str = "",
        extra_info: str = "",
        output_path: str = "",
        **kwargs,
    ) -> AIMessage:
        """
        Write a system design.

        Args:
            user_requirement (str): The user's requirements for the system design.
            prd_filename (str, optional): The filename of the Product Requirement Document (PRD).
            exists_design_filename (str, optional): The filename of the existing design document.
            extra_info (str, optional): Additional information to be included in the system design.
            output_path (str, optional): The output path where the system design should be saved.

        Returns:
            AIMessage: An AIMessage object containing the system design.

        Example:
            # Write a new system design.
            >>> user_requirement = "Your user requirements"
            >>> extra_info = "Your extra information"
            >>> action = WriteDesign()
            >>> result = await action.run(user_requirement=user_requirement, extra_info=extra_info)
            >>> print(result.content)
            The design is balabala...

            # Modify an exists system design.
            >>> user_requirement = "Your user requirements"
            >>> extra_info = "Your extra information"
            >>> exists_design_filename = "/path/to/exists/design/filename"
            >>> action = WriteDesign()
            >>> result = await action.run(user_requirement=user_requirement, extra_info=extra_info, exists_design_filename=exists_design_filename)
            >>> print(result.content)
            The design is balabala...

            # Write a new system design with the given PRD(Product Requirement Document).
            >>> user_requirement = "Your user requirements"
            >>> extra_info = "Your extra information"
            >>> prd_filename = "/path/to/prd/filename"
            >>> action = WriteDesign()
            >>> result = await action.run(user_requirement=user_requirement, extra_info=extra_info, prd_filename=prd_filename)
            >>> print(result.content)
            The design is balabala...

            # Modify an exists system design with the given PRD(Product Requirement Document).
            >>> user_requirement = "Your user requirements"
            >>> extra_info = "Your extra information"
            >>> prd_filename = "/path/to/prd/filename"
            >>> exists_design_filename = "/path/to/exists/design/filename"
            >>> action = WriteDesign()
            >>> result = await action.run(user_requirement=user_requirement, extra_info=extra_info, exists_design_filename=exists_design_filename, prd_filename=prd_filename)
            >>> print(result.content)
            The design is balabala...

            # Write a new system design and save to the directory.
            >>> user_requirement = "Your user requirements"
            >>> extra_info = "Your extra information"
            >>> output_path = "/path/to/save/"
            >>> action = WriteDesign()
            >>> result = await action.run(user_requirement=user_requirement, extra_info=extra_info, output_path=output_path)
            >>> print(result.content)
            System Design filename: "/path/to/design/filename"

            # Modify an exists system design and save to the directory.
            >>> user_requirement = "Your user requirements"
            >>> extra_info = "Your extra information"
            >>> exists_design_filename = "/path/to/exists/design/filename"
            >>> output_path = "/path/to/save/"
            >>> action = WriteDesign()
            >>> result = await action.run(user_requirement=user_requirement, extra_info=extra_info, exists_design_filename=exists_design_filename)
            >>> print(result.content)
            System Design filename: "/path/to/design/filename"

            # Write a new system design with the given PRD(Product Requirement Document) and save to the directory.
            >>> user_requirement = "Your user requirements"
            >>> extra_info = "Your extra information"
            >>> prd_filename = "/path/to/prd/filename"
            >>> output_path = "/path/to/save/"
            >>> action = WriteDesign()
            >>> result = await action.run(user_requirement=user_requirement, extra_info=extra_info, prd_filename=prd_filename)
            >>> print(result.content)
            System Design filename: "/path/to/design/filename"

            # Modify an exists system design with the given PRD(Product Requirement Document) and save to the directory.
            >>> user_requirement = "Your user requirements"
            >>> extra_info = "Your extra information"
            >>> prd_filename = "/path/to/prd/filename"
            >>> exists_design_filename = "/path/to/exists/design/filename"
            >>> output_path = "/path/to/save/"
            >>> action = WriteDesign()
            >>> result = await action.run(user_requirement=user_requirement, extra_info=extra_info, exists_design_filename=exists_design_filename, prd_filename=prd_filename)
            >>> print(result.content)
            System Design filename: "/path/to/design/filename"
        """
        if not with_messages:
            return await self._execute_api(
                user_requirement=user_requirement,
                prd_filename=prd_filename,
                exists_design_filename=exists_design_filename,
                extra_info=extra_info,
                output_path=output_path,
            )

        self.input_args = with_messages[0].instruct_content
        self.repo = ProjectRepo(self.input_args.project_path)
        changed_prds = self.input_args.changed_prd_filenames
        changed_system_designs = [
            str(self.repo.docs.system_design.workdir / i)
            for i in list(self.repo.docs.system_design.changed_files.keys())
        ]

        # For those PRDs and design documents that have undergone changes, regenerate the design content.
        changed_files = Documents()
        for filename in changed_prds:
            doc = await self._update_system_design(filename=filename)
            changed_files.docs[filename] = doc

        for filename in changed_system_designs:
            if filename in changed_files.docs:
                continue
            doc = await self._update_system_design(filename=filename)
            changed_files.docs[filename] = doc
        if not changed_files.docs:
            logger.info("Nothing has changed.")
        # Wait until all files under `docs/system_designs/` are processed before sending the publish message,
        # leaving room for global optimization in subsequent steps.
        kvs = self.input_args.model_dump()
        kvs["changed_system_design_filenames"] = [
            str(self.repo.docs.system_design.workdir / i)
            for i in list(self.repo.docs.system_design.changed_files.keys())
        ]
        return AIMessage(
            content="Designing is complete. "
            + "\n".join(
                list(self.repo.docs.system_design.changed_files.keys())
                + list(self.repo.resources.data_api_design.changed_files.keys())
                + list(self.repo.resources.seq_flow.changed_files.keys())
            ),
            instruct_content=AIMessage.create_instruct_value(kvs=kvs, class_name="WriteDesignOutput"),
            cause_by=self,
        )

    async def _new_system_design(self, context):
        node = await DESIGN_API_NODE.fill(context=context, llm=self.llm, schema=self.prompt_schema)
        return node

    async def _merge(self, prd_doc, system_design_doc):
        context = NEW_REQ_TEMPLATE.format(old_design=system_design_doc.content, context=prd_doc.content)
        node = await REFINED_DESIGN_NODE.fill(context=context, llm=self.llm, schema=self.prompt_schema)
        system_design_doc.content = node.instruct_content.model_dump_json()
        return system_design_doc

    async def _update_system_design(self, filename) -> Document:
        root_relative_path = Path(filename).relative_to(self.repo.workdir)
        prd = await Document.load(filename=filename, project_path=self.repo.workdir)
        old_system_design_doc = await self.repo.docs.system_design.get(root_relative_path.name)
        async with DocsReporter(enable_llm_stream=True) as reporter:
            await reporter.async_report({"type": "design"}, "meta")
            if not old_system_design_doc:
                system_design = await self._new_system_design(context=prd.content)
                doc = await self.repo.docs.system_design.save(
                    filename=prd.filename,
                    content=system_design.instruct_content.model_dump_json(),
                    dependencies={prd.root_relative_path},
                )
            else:
                doc = await self._merge(prd_doc=prd, system_design_doc=old_system_design_doc)
                await self.repo.docs.system_design.save_doc(doc=doc, dependencies={prd.root_relative_path})
            await self._save_data_api_design(doc)
            await self._save_seq_flow(doc)
            md = await self.repo.resources.system_design.save_pdf(doc=doc)
            await reporter.async_report(self.repo.workdir / md.root_relative_path, "path")
        return doc

    async def _save_data_api_design(self, design_doc):
        m = json.loads(design_doc.content)
        data_api_design = m.get(DATA_STRUCTURES_AND_INTERFACES.key) or m.get(REFINED_DATA_STRUCTURES_AND_INTERFACES.key)
        if not data_api_design:
            return
        pathname = self.repo.workdir / DATA_API_DESIGN_FILE_REPO / Path(design_doc.filename).with_suffix("")
        await self._save_mermaid_file(data_api_design, pathname)
        logger.info(f"Save class view to {str(pathname)}")

    async def _save_seq_flow(self, design_doc):
        m = json.loads(design_doc.content)
        seq_flow = m.get(PROGRAM_CALL_FLOW.key) or m.get(REFINED_PROGRAM_CALL_FLOW.key)
        if not seq_flow:
            return
        pathname = self.repo.workdir / Path(SEQ_FLOW_FILE_REPO) / Path(design_doc.filename).with_suffix("")
        await self._save_mermaid_file(seq_flow, pathname)
        logger.info(f"Saving sequence flow to {str(pathname)}")

    async def _save_mermaid_file(self, data: str, pathname: Path):
        pathname.parent.mkdir(parents=True, exist_ok=True)
        await mermaid_to_file(self.config.mermaid.engine, data, pathname)
        image_path = pathname.parent / f"{pathname.name}.png"
        if image_path.exists():
            await GalleryReporter().async_report(image_path, "path")

    async def _execute_api(
        self,
        user_requirement: str = "",
        prd_filename: str = "",
        exists_design_filename: str = "",
        extra_info: str = "",
        output_path: str = "",
    ) -> AIMessage:
        context = to_markdown_code_block(user_requirement)
        if extra_info:
            context = to_markdown_code_block(extra_info)
        if prd_filename:
            prd_content = await aread(filename=prd_filename)
            context += to_markdown_code_block(prd_content)
        if not exists_design_filename:
            node = await self._new_system_design(context=context)
            design = Document(content=node.instruct_content.model_dump_json())
        else:
            old_design_content = await aread(filename=exists_design_filename)
            design = await self._merge(
                prd_doc=Document(content=context), system_design_doc=Document(content=old_design_content)
            )

        if not output_path:
            return AIMessage(content=design.instruct_content.model_dump_json())
        output_filename = Path(output_path) / f"{uuid.uuid4().hex}.json"
        await awrite(filename=output_filename, data=design.content)
        return AIMessage(content=f'System Design filename: "{str(output_filename)}"')
